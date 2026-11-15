/*
 * compose.c - ARGB image helpers (see compose.h).
 */
#include "compose.h"

void cp_from_clut(uint8_t *dst, const uint8_t *px, uint32_t n,
                  const uint8_t *palette, uint32_t palsize, int32_t transparent)
{
	uint32_t i;
	for (i = 0; i < n; i++, dst += 4)
	{
		uint32_t c = px[i];
		if ((int32_t)c == transparent)
		{
			dst[0] = dst[1] = dst[2] = dst[3] = 0;
		}
		else if (c < palsize)
		{
			dst[0] = 255;
			dst[1] = palette[3 * c];
			dst[2] = palette[3 * c + 1];
			dst[3] = palette[3 * c + 2];
		}
		else
		{
			dst[0] = 255;
			dst[1] = dst[2] = dst[3] = 0;
		}
	}
}

/* Workbench pens 0-7 (0 is the background: transparent) */
static const uint8_t pens[8][3] =
{
	{ 0xAA, 0xAA, 0xAA }, { 0x00, 0x00, 0x00 }, { 0xFF, 0xFF, 0xFF }, { 0x66, 0x88, 0xBB },
	{ 0x99, 0x99, 0x99 }, { 0xBB, 0xBB, 0xBB }, { 0xBB, 0xAA, 0x99 }, { 0xFF, 0xAA, 0x22 }
};

void cp_from_planar(uint8_t *dst, uint32_t width, uint32_t height,
                    const uint8_t *planes, uint32_t depth)
{
	uint32_t rowbytes = ((width + 15) / 16) * 2, planesize = rowbytes * height, x, y, d;
	for (y = 0; y < height; y++)
		for (x = 0; x < width; x++, dst += 4)
		{
			uint32_t c = 0;
			for (d = 0; d < depth; d++)
				if (planes[d * planesize + y * rowbytes + x / 8] & (0x80 >> (x & 7)))
					c |= 1u << d;
			if (c == 0)
			{
				dst[0] = dst[1] = dst[2] = dst[3] = 0;
			}
			else if (c < 8)
			{
				dst[0] = 255;
				dst[1] = pens[c][0]; dst[2] = pens[c][1]; dst[3] = pens[c][2];
			}
			else
			{
				dst[0] = 255;
				dst[1] = dst[2] = dst[3] = (uint8_t)c;
			}
		}
}

void cp_place_centred(uint8_t *dst, uint32_t dw, uint32_t dh,
                      const uint8_t *src, uint32_t sw, uint32_t sh)
{
	int32_t ox = ((int32_t)dw - (int32_t)sw) / 2, oy = ((int32_t)dh - (int32_t)sh) / 2;
	uint32_t i, x, y;
	for (i = 0; i < dw * dh * 4; i++) dst[i] = 0;
	for (y = 0; y < sh; y++)
	{
		int32_t ty = oy + (int32_t)y;
		if (ty < 0 || ty >= (int32_t)dh) continue;
		for (x = 0; x < sw; x++)
		{
			int32_t tx = ox + (int32_t)x;
			const uint8_t *s;
			uint8_t *t;
			if (tx < 0 || tx >= (int32_t)dw) continue;
			s = src + 4 * (y * sw + x);
			t = dst + 4 * ((uint32_t)ty * dw + (uint32_t)tx);
			t[0] = s[0]; t[1] = s[1]; t[2] = s[2]; t[3] = s[3];
		}
	}
}

/* ---- composition ---- */

static int resolve(int method, int defmethod) { return method == ES_DEFAULT ? defmethod : method; }

void cp_method(uint8_t *px, uint32_t n, int method)
{
	uint32_t i, c;
	switch (method)
	{
		case ES_DARK:     /* 25 % darker */
			for (i = 0; i < n; i++, px += 4)
				for (c = 1; c < 4; c++) px[c] = (uint8_t)((px[c] * 3u + 2) / 4);
			break;
		case ES_BRIGHT:   /* 25 % of the way to white */
			for (i = 0; i < n; i++, px += 4)
				for (c = 1; c < 4; c++) px[c] = (uint8_t)((px[c] * 3u + 255 + 2) / 4);
			break;
		case ES_GRAY:     /* luminance, Rec. 601 weights */
			for (i = 0; i < n; i++, px += 4)
			{
				uint8_t l = (uint8_t)((px[1] * 77u + px[2] * 150u + px[3] * 29u + 128) >> 8);
				px[1] = px[2] = px[3] = l;
			}
			break;
		default:          /* NONE; SHADOW and GLOW are layers (cp_effect) */
			break;
	}
}

/* One axis: in[i * is] for i < s -> out[o * os] for o < d. Values are premultiplied,
 * at most 65025; all sums stay below 2^32 for s, d <= 1024. */
static void resample(const uint32_t *in, uint32_t is, uint32_t s, uint32_t *out, uint32_t os, uint32_t d)
{
	uint32_t o;
	if (d == s)
	{
		for (o = 0; o < d; o++) out[o * os] = in[o * is];
	}
	else if (d < s)
	{
		/* area average: out pixel o covers [o*s, (o+1)*s), in pixel j covers [j*d, (j+1)*d) */
		for (o = 0; o < d; o++)
		{
			uint32_t lo = o * s, hi = lo + s, j = lo / d, sum = 0;
			for (; j * d < hi; j++)
			{
				uint32_t a = j * d > lo ? j * d : lo, b = (j + 1) * d < hi ? (j + 1) * d : hi;
				sum += in[j * is] * (b - a);
			}
			out[o * os] = (sum + s / 2) / s;
		}
	}
	else
	{
		/* bilinear, pixel centres aligned, 8 bits of fraction */
		for (o = 0; o < d; o++)
		{
			int32_t num = (int32_t)((2 * o + 1) * s) - (int32_t)d;
			uint32_t p = num <= 0 ? 0 : (uint32_t)num * 256 / (2 * d), j = p >> 8, f = p & 255;
			if (j >= s - 1) { j = s - 1; f = 0; }
			out[o * os] = (in[j * is] * (256 - f) + (f ? in[(j + 1) * is] * f : 0) + 128) >> 8;
		}
	}
}

int cp_scale(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
             const CPMem *tmp)
{
	uint32_t maxin = sw > sh ? sw : sh, maxout = dw > dh ? dw : dh, x, y, c;
	uint32_t tsize = dw * sh * 4 * sizeof(uint16_t), bsize = (maxin + maxout) * 4 * sizeof(uint32_t);
	uint8_t *mem;
	uint16_t *t;
	uint32_t *bin, *bout;

	if (!dw || !dh || !sw || !sh) return 0;
	if (!(mem = tmp->alloc(tmp->ctx, tsize + bsize))) return -1;
	bin = (uint32_t *)mem;
	bout = bin + maxin * 4;
	t = (uint16_t *)(bout + maxout * 4);

	/* rows: sw -> dw, premultiplied (alpha as a*255, colour as c*a) */
	for (y = 0; y < sh; y++)
	{
		const uint8_t *s = src + y * sw * 4;
		for (x = 0; x < sw; x++, s += 4)
		{
			bin[x * 4]     = s[0] * 255u;
			bin[x * 4 + 1] = s[1] * (uint32_t)s[0];
			bin[x * 4 + 2] = s[2] * (uint32_t)s[0];
			bin[x * 4 + 3] = s[3] * (uint32_t)s[0];
		}
		for (c = 0; c < 4; c++) resample(bin + c, 4, sw, bout + c, 4, dw);
		for (x = 0; x < dw * 4; x++) t[y * dw * 4 + x] = (uint16_t)bout[x];
	}
	/* columns: sh -> dh, back to straight alpha */
	for (x = 0; x < dw; x++)
	{
		for (y = 0; y < sh; y++)
			for (c = 0; c < 4; c++) bin[y * 4 + c] = t[(y * dw + x) * 4 + c];
		for (c = 0; c < 4; c++) resample(bin + c, 4, sh, bout + c, 4, dh);
		for (y = 0; y < dh; y++)
		{
			uint8_t *o = dst + (y * dw + x) * 4;
			uint32_t A = bout[y * 4];
			if (A == 0)
			{
				o[0] = o[1] = o[2] = o[3] = 0;
				continue;
			}
			o[0] = (uint8_t)((A + 127) / 255);
			for (c = 1; c < 4; c++)
			{
				uint32_t v = (bout[y * 4 + c] * 255 + A / 2) / A;
				o[c] = (uint8_t)(v > 255 ? 255 : v);
			}
		}
	}
	tmp->free(tmp->ctx, mem);
	return 0;
}

/* One pixel of colour rgb with alpha sa (1..254) over d ("source over"). */
static void over1(uint8_t *d, uint32_t sa, const uint8_t *rgb)
{
	uint32_t ab = d[0] * (255 - sa);   /* what shows of d, scaled by 255 */
	uint32_t oa = sa * 255 + ab;       /* result alpha, scaled by 255 */
	uint32_t c;
	for (c = 0; c < 3; c++)
		d[c + 1] = (uint8_t)((rgb[c] * sa * 255 + d[c + 1] * ab + oa / 2) / oa);
	d[0] = (uint8_t)((oa + 127) / 255);
}

void cp_over(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
             int32_t x0, int32_t y0)
{
	uint32_t x, y;
	for (y = 0; y < sh; y++)
	{
		int32_t ty = y0 + (int32_t)y;
		if (ty < 0 || ty >= (int32_t)dh) continue;
		for (x = 0; x < sw; x++)
		{
			int32_t tx = x0 + (int32_t)x;
			const uint8_t *s = src + (y * sw + x) * 4;
			uint8_t *d;
			uint32_t sa;
			if (tx < 0 || tx >= (int32_t)dw || (sa = s[0]) == 0) continue;
			d = dst + ((uint32_t)ty * dw + (uint32_t)tx) * 4;
			if (sa == 255)
			{
				d[0] = s[0]; d[1] = s[1]; d[2] = s[2]; d[3] = s[3];
				continue;
			}
			over1(d, sa, s + 1);
		}
	}
}

/* Box blur of a w x h alpha mask, radius r, zero outside; t is scratch of the same size. */
static void box(uint8_t *m, uint8_t *t, uint32_t w, uint32_t h, uint32_t r)
{
	uint32_t x, y, n = 2 * r + 1, i, sum;
	if (!r) return;
	for (y = 0; y < h; y++)                 /* rows: m -> t */
	{
		const uint8_t *row = m + y * w;
		uint8_t *o = t + y * w;
		for (sum = 0, i = 0; i <= r && i < w; i++) sum += row[i];
		for (x = 0; x < w; x++)
		{
			o[x] = (uint8_t)((sum + n / 2) / n);
			if (x + r + 1 < w) sum += row[x + r + 1];
			if (x >= r) sum -= row[x - r];
		}
	}
	for (x = 0; x < w; x++)                 /* columns: t -> m */
	{
		for (sum = 0, i = 0; i <= r && i < h; i++) sum += t[i * w + x];
		for (y = 0; y < h; y++)
		{
			m[y * w + x] = (uint8_t)((sum + n / 2) / n);
			if (y + r + 1 < h) sum += t[(y + r + 1) * w + x];
			if (y >= r) sum -= t[(y - r) * w + x];
		}
	}
}

/* Grow a mask: the maximum within radius g (a square); t is scratch. */
static void dilate(uint8_t *m, uint8_t *t, uint32_t w, uint32_t h, uint32_t g)
{
	uint32_t x, y;
	int32_t k;
	for (y = 0; y < h; y++)
		for (x = 0; x < w; x++)
		{
			uint8_t v = 0;
			for (k = -(int32_t)g; k <= (int32_t)g; k++)
			{
				int32_t xx = (int32_t)x + k;
				if (xx >= 0 && xx < (int32_t)w && m[y * w + xx] > v) v = m[y * w + xx];
			}
			t[y * w + x] = v;
		}
	for (y = 0; y < h; y++)
		for (x = 0; x < w; x++)
		{
			uint8_t v = 0;
			for (k = -(int32_t)g; k <= (int32_t)g; k++)
			{
				int32_t yy = (int32_t)y + k;
				if (yy >= 0 && yy < (int32_t)h && t[yy * w + x] > v) v = t[yy * w + x];
			}
			m[y * w + x] = v;
		}
}

static int is_effect(int method) { return method == ES_SHADOW || method == ES_GLOW; }

int cp_effect(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
              int32_t x, int32_t y, int method, const CPPrefs *p, const CPMem *tmp)
{
	uint32_t r, g = 0, m, mw, mh, i, j, opacity;
	int32_t ox = 0, oy = 0, lx, ly;
	uint8_t rgb[3] = { 0, 0, 0 }, *mask, *t;

	if (method == ES_SHADOW)
	{
		r = p->shadowblur;
		ox = p->shadowx;
		oy = p->shadowy;
		opacity = p->shadowopacity;
		m = 2 * r;                      /* two blur passes reach 2r further */
	}
	else if (method == ES_GLOW)
	{
		g = p->glowsize ? p->glowsize : 1;
		r = g;
		opacity = p->glowopacity;
		rgb[0] = p->glowrgb[0]; rgb[1] = p->glowrgb[1]; rgb[2] = p->glowrgb[2];
		m = g + 2 * r;
	}
	else
		return 0;
	if (!opacity) return 0;
	if (opacity > 100) opacity = 100;

	mw = sw + 2 * m;
	mh = sh + 2 * m;
	lx = x + ox - (int32_t)m;
	ly = y + oy - (int32_t)m;
	if (lx >= (int32_t)dw || ly >= (int32_t)dh || lx + (int32_t)mw <= 0 || ly + (int32_t)mh <= 0)
		return 0;   /* the layer is entirely outside the image */
	if (!(mask = tmp->alloc(tmp->ctx, mw * mh * 2))) return -1;
	t = mask + mw * mh;
	for (i = 0; i < mw * mh; i++) mask[i] = 0;
	for (j = 0; j < sh; j++)
		for (i = 0; i < sw; i++)
			mask[(j + m) * mw + i + m] = src[(j * sw + i) * 4];
	if (g) dilate(mask, t, mw, mh, g);
	box(mask, t, mw, mh, r);
	box(mask, t, mw, mh, r);

	for (j = 0; j < mh; j++)
	{
		int32_t ty = ly + (int32_t)j;
		if (ty < 0 || ty >= (int32_t)dh) continue;
		for (i = 0; i < mw; i++)
		{
			int32_t tx = lx + (int32_t)i;
			uint32_t a = mask[j * mw + i];
			uint8_t *d;
			if (!a || tx < 0 || tx >= (int32_t)dw) continue;
			a = (a * opacity + 50) / 100;
			if (!a) continue;
			d = dst + ((uint32_t)ty * dw + (uint32_t)tx) * 4;
			if (a >= 255) { d[0] = 255; d[1] = rgb[0]; d[2] = rgb[1]; d[3] = rgb[2]; }
			else over1(d, a, rgb);
		}
	}
	tmp->free(tmp->ctx, mask);
	return 0;
}

/* SHADOW/GLOW on a whole image (IMAGE=...,SHADOW): the effect goes under it. */
static int effect_under(uint8_t *img, uint32_t w, uint32_t h, int method, const CPPrefs *p, const CPMem *tmp)
{
	uint8_t *copy;
	uint32_t i;
	if (!(copy = tmp->alloc(tmp->ctx, w * h * 4))) return -1;
	for (i = 0; i < w * h * 4; i++) { copy[i] = img[i]; img[i] = 0; }
	if (cp_effect(img, w, h, copy, w, h, 0, 0, method, p, tmp) != 0)
	{
		for (i = 0; i < w * h * 4; i++) img[i] = copy[i];
		tmp->free(tmp->ctx, copy);
		return -1;
	}
	cp_over(img, w, h, copy, w, h, 0, 0);
	tmp->free(tmp->ctx, copy);
	return 0;
}

/* A colour method changes the pixels, an effect adds a layer under them. */
static int apply_image_method(uint8_t *img, uint32_t w, uint32_t h, int method, const CPPrefs *p, const CPMem *tmp)
{
	if (is_effect(method)) return effect_under(img, w, h, method, p, tmp);
	cp_method(img, w * h, method);
	return 0;
}

void cp_emblem_size(const ESEmblem *e, uint32_t sw, uint32_t sh, uint32_t *w, uint32_t *h)
{
	uint32_t ew = e->width > 0 ? (uint32_t)e->width : 0, eh = e->height > 0 ? (uint32_t)e->height : 0;
	if (!ew && !eh) { ew = sw; eh = sh; }
	else if (!ew) { ew = (sw * eh + sh / 2) / sh; if (!ew) ew = 1; }
	else if (!eh) { eh = (sh * ew + sw / 2) / sw; if (!eh) eh = 1; }
	*w = ew;
	*h = eh;
}

static int draw_emblem(uint8_t *dst, uint32_t w, uint32_t h, const CPImage *src, const char *name,
                       uint32_t ew, uint32_t eh, int32_t x, int32_t y, int method, const CPPrefs *p,
                       const CPMem *tmp, const CPScaleCache *cache)
{
	uint8_t *e;
	const uint8_t *cached = 0;
	uint32_t i;
	if (!is_effect(method) && (x >= (int32_t)w || y >= (int32_t)h || x + (int32_t)ew <= 0 || y + (int32_t)eh <= 0))
		return 0;   /* entirely outside: nothing to draw (an effect may still reach in) */
	if (!(e = tmp->alloc(tmp->ctx, ew * eh * 4))) return -1;
	if (ew == src->w && eh == src->h)
		for (i = 0; i < ew * eh * 4; i++) e[i] = src->px[i];
	else if (name && cache && (cached = cache->find(cache->ctx, name, ew, eh)))
		for (i = 0; i < ew * eh * 4; i++) e[i] = cached[i];
	else if (cp_scale(e, ew, eh, src->px, src->w, src->h, tmp) != 0)
	{
		tmp->free(tmp->ctx, e);
		return -1;
	}
	else if (name && cache)
		cache->store(cache->ctx, name, ew, eh, e);   /* before the method changes it */
	if (is_effect(method))
	{
		if (cp_effect(dst, w, h, e, ew, eh, x, y, method, p, tmp) != 0)
		{
			tmp->free(tmp->ctx, e);
			return -1;
		}
	}
	else
		cp_method(e, ew * eh, method);
	cp_over(dst, w, h, e, ew, eh, x, y);
	tmp->free(tmp->ctx, e);
	return 0;
}

static int usable(const CPImage *im, uint32_t max)
{
	return im->px && im->w >= 1 && im->h >= 1 && im->w <= max && im->h <= max;
}

int cp_compose(const ESpec *spec, const CPPrefs *prefs, cp_image_fn get, void *gctx,
               const CPMem *out, const CPMem *tmp, const CPScaleCache *cache, CPResult *res)
{
	CPImage def[2], base[2], em[2];
	int hasdef[2] = { 0, 0 }, hasbase[2] = { 0, 0 }, hasem[2] = { 0, 0 }, k;
	uint32_t w, h, ew[2] = { 0, 0 }, eh[2] = { 0, 0 }, i;
	uint8_t *img[2] = { 0, 0 };

	res->img[0] = res->img[1] = 0;
	res->w = res->h = 0;
	for (k = 0; k < 2; k++)
	{
		def[k].px = base[k].px = em[k].px = 0;
		/* default images: larger than an icon can be = ignored like a missing one */
		if (spec->image[k].set && get(gctx, spec->image[k].name, 0, &def[k]) && usable(&def[k], CP_MAXCANVAS))
			hasdef[k] = 1;
		/* base images: the default one, else the icon's own */
		if (hasdef[k]) { base[k] = def[k]; hasbase[k] = 1; }
		else if (get(gctx, 0, k, &base[k]) && usable(&base[k], CP_MAXSOURCE)) hasbase[k] = 1;
	}
	if (!hasbase[0] || !usable(&base[0], CP_MAXCANVAS)) return 0;
	w = base[0].w;
	h = base[0].h;

	for (k = 0; k < 2; k++)
	{
		const ESEmblem *e = &spec->emblem[k];
		int found;
		if (!e->set || (k == 1 && !hasbase[1])) continue;   /* no selected image: no selected emblem */
		if (e->internal)
		{
			/* the icon's own image as the emblem: only on a default image (spec) */
			if (!hasdef[k]) continue;
			found = get(gctx, 0, k, &em[k]) || (k == 1 && get(gctx, 0, 0, &em[k]));
		}
		else
			found = get(gctx, e->name, 0, &em[k]);
		if (!found || !usable(&em[k], CP_MAXSOURCE)) continue;
		cp_emblem_size(e, em[k].w, em[k].h, &ew[k], &eh[k]);
		if (ew[k] > CP_MAXEMBLEM || eh[k] > CP_MAXEMBLEM) continue;
		hasem[k] = 1;
	}
	if (!hasdef[0] && !hasdef[1] && !hasem[0] && !hasem[1]) return 0;

	if (!(img[0] = out->alloc(out->ctx, w * h * 4))) goto nomem;
	for (i = 0; i < w * h * 4; i++) img[0][i] = base[0].px[i];
	if (hasdef[0] && apply_image_method(img[0], w, h, resolve(spec->image[0].method, prefs->imagemethod), prefs, tmp) != 0)
		goto nomem;
	if (hasbase[1])
	{
		if (!(img[1] = out->alloc(out->ctx, w * h * 4))) goto nomem;
		cp_place_centred(img[1], w, h, base[1].px, base[1].w, base[1].h);
		if (hasdef[1] && apply_image_method(img[1], w, h, resolve(spec->image[1].method, prefs->imagemethod), prefs, tmp) != 0)
			goto nomem;
	}
	for (k = 0; k < 2; k++)
		if (hasem[k] && draw_emblem(img[k], w, h, &em[k], spec->emblem[k].internal ? 0 : spec->emblem[k].name,
		                            ew[k], eh[k], spec->emblem[k].x, spec->emblem[k].y,
		                            resolve(spec->emblem[k].method, prefs->emblemmethod), prefs, tmp, cache) != 0)
			goto nomem;
	res->img[0] = img[0];
	res->img[1] = img[1];
	res->w = w;
	res->h = h;
	return 1;

nomem:
	if (out->free)
		for (k = 0; k < 2; k++)
			if (img[k]) out->free(out->ctx, img[k]);
	return -1;
}
