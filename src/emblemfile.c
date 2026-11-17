/*
 * emblemfile.c - Emblem icon file format (docs/format.md), portable C.
 * No C library calls, so it links into the icon module as it is.
 */
#include "emblemfile.h"

#define EF_MAXPLANAR 1024   /* old planar icons may be wider than chunky ones */

static uint16_t g16(const uint8_t *p) { return (uint16_t)((p[0] << 8) | p[1]); }
static uint32_t g32(const uint8_t *p)
{
	return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}
static void p16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v; }
static void p32(uint8_t *p, uint32_t v)
{
	p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v;
}
static int idis(const uint8_t *p, const char *id)
{
	return p[0] == (uint8_t)id[0] && p[1] == (uint8_t)id[1] && p[2] == (uint8_t)id[2] && p[3] == (uint8_t)id[3];
}
static void copybytes(uint8_t *d, const uint8_t *s, uint32_t n) { while (n--) *d++ = *s++; }
static void zerobytes(void *p, uint32_t n) { uint8_t *d = p; while (n--) *d++ = 0; }

int ef_is_emblem(const uint8_t *buf, uint32_t len)
{
	return len >= 24 && idis(buf, "FORM") && idis(buf + 8, "EMBL") && idis(buf + 12, "HEAD")
		&& g32(buf + 16) >= 24;
}

uint32_t ef_file_size(const uint8_t *buf, uint32_t len)
{
	uint32_t s;
	if (!ef_is_emblem(buf, len)) return 0;
	s = g32(buf + 4);
	if (s < 4 + 8 + 24 || s > 0x7FFFFFF0u) return 0;
	return s + 8;
}

uint32_t ef_image_datalen(const EFImage *img)
{
	uint32_t w = img->width, h = img->height;
	uint32_t maxw = img->kind == EF_PLANAR ? EF_MAXPLANAR : EF_MAXDIM;
	if (w < 1 || h < 1 || w > maxw || h > maxw) return 0;
	switch (img->kind)
	{
		case EF_ARGB:   return 4 * w * h;
		case EF_CLUT:   return w * h;
		case EF_PLANAR:
			if (img->depth < 1 || img->depth > 8) return 0;
			return img->depth * h * ((w + 15) / 16) * 2;
	}
	return 0;
}

uint32_t ef_count_tooltypes(const char *tt, uint32_t len)
{
	uint32_t n = 0, i;
	if (!tt) return 0;
	for (i = 0; i < len; i++)
		if (tt[i] == 0) n++;
	return n;
}

static int parse_image(const uint8_t *d, uint32_t clen, EFImage *img)
{
	uint32_t p = 8, expect;

	zerobytes(img, sizeof(*img));
	if (clen < 8) return EF_ERR_CORRUPT;
	img->kind   = d[1];
	img->comp   = d[2];
	img->width  = g16(d + 4);
	img->height = g16(d + 6);
	img->transparent = -1;
	if (img->kind == EF_CLUT)
	{
		if (clen < p + 4) return EF_ERR_CORRUPT;
		img->palsize = g16(d + p);
		img->transparent = (int16_t)g16(d + p + 2);
		if (img->palsize < 1 || img->palsize > 256) return EF_ERR_CORRUPT;
		if (img->transparent < -1 || img->transparent >= (int)img->palsize) return EF_ERR_CORRUPT;
		p += 4;
		if (clen < p + img->palsize * 3u) return EF_ERR_CORRUPT;
		img->palette = d + p;
		p += img->palsize * 3u;
	}
	else if (img->kind == EF_PLANAR)
	{
		if (clen < p + 8) return EF_ERR_CORRUPT;
		img->left       = (int16_t)g16(d + p);
		img->top        = (int16_t)g16(d + p + 2);
		img->depth      = g16(d + p + 4);
		img->planepick  = d[p + 6];
		img->planeonoff = d[p + 7];
		p += 8;
	}
	else if (img->kind != EF_ARGB)
		return EF_ERR_CORRUPT;

	if (clen < p + 4) return EF_ERR_CORRUPT;
	img->datalen = g32(d + p);
	p += 4;
	expect = ef_image_datalen(img);
	if (!expect || img->datalen != expect) return EF_ERR_CORRUPT;
	img->data = d + p;
	img->complen = clen - p;
	if (img->comp == EF_RAW)
	{
		if (img->complen < img->datalen) return EF_ERR_CORRUPT;
	}
	else if (img->comp != EF_ZLIB || img->complen == 0)
		return EF_ERR_CORRUPT;
	img->present = 1;
	return EF_OK;
}

int ef_parse(const uint8_t *buf, uint32_t len, EFIcon *ic)
{
	uint32_t total, pos = EF_HEADPOS;
	int seenhead = 0, r;

	zerobytes(ic, sizeof(*ic));
	ic->img[0].transparent = ic->img[1].transparent = -1;
	ic->planar[0].transparent = ic->planar[1].transparent = -1;
	if (!ef_is_emblem(buf, len)) return EF_ERR_NOTEMBLEM;
	total = ef_file_size(buf, len);
	if (!total || total > len) return EF_ERR_CORRUPT;

	while (pos + 8 <= total)
	{
		const uint8_t *ch = buf + pos, *d = ch + 8;
		uint32_t clen = g32(ch + 4), next;

		if (clen > total - pos - 8) return EF_ERR_CORRUPT;
		next = pos + 8 + clen + (clen & 1);
		if (next > total) next = total;   /* a missing pad byte at the very end is fine */

		if (idis(ch, "HEAD"))
		{
			if (pos != EF_HEADPOS || clen < 24 || seenhead) return EF_ERR_CORRUPT;
			if (g16(d) > EF_VERSION) return EF_ERR_VERSION;
			ic->type      = d[2];
			ic->frameless = d[3] & 1;
			ic->aspect    = d[4];
			ic->gflags    = g16(d + 6);
			ic->gwidth    = g16(d + 8);
			ic->gheight   = g16(d + 10);
			ic->curx      = (int32_t)g32(d + 12);
			ic->cury      = (int32_t)g32(d + 16);
			ic->stack     = (int32_t)g32(d + 20);
			seenhead = 1;
		}
		else if (idis(ch, "DRAW"))
		{
			if (clen < 22 || ic->hasdrawer) return EF_ERR_CORRUPT;
			ic->hasdrawer  = 1;
			ic->dleft      = (int16_t)g16(d);
			ic->dtop       = (int16_t)g16(d + 2);
			ic->dwidth     = (int16_t)g16(d + 4);
			ic->dheight    = (int16_t)g16(d + 6);
			ic->dcurx      = (int32_t)g32(d + 8);
			ic->dcury      = (int32_t)g32(d + 12);
			ic->dflags     = g32(d + 16);
			ic->dviewmodes = g16(d + 20);
		}
		else if (idis(ch, "DEFT"))
		{
			if (ic->deftool) return EF_ERR_CORRUPT;
			ic->deftool = (const char *)d;
			ic->deftoollen = clen;
		}
		else if (idis(ch, "TWIN"))
		{
			if (ic->toolwindow) return EF_ERR_CORRUPT;
			ic->toolwindow = (const char *)d;
			ic->toolwindowlen = clen;
		}
		else if (idis(ch, "TTYP"))
		{
			if (ic->tooltypes) return EF_ERR_CORRUPT;
			if (clen && d[clen - 1] != 0) return EF_ERR_CORRUPT;
			ic->tooltypes = (const char *)d;
			ic->tooltypeslen = clen;
		}
		else if (idis(ch, "ESET"))
		{
			if (ic->settings) return EF_ERR_CORRUPT;
			if (clen && d[clen - 1] != 0) return EF_ERR_CORRUPT;
			ic->settings = (const char *)d;
			ic->settingslen = clen;
		}
		else if (idis(ch, "IMAG"))
		{
			EFImage img, *slot;
			uint8_t state = clen ? d[0] : 0xFF;
			if (state > 1) return EF_ERR_CORRUPT;
			if ((r = parse_image(d, clen, &img)) != EF_OK) return r;
			slot = img.kind == EF_PLANAR ? &ic->planar[state] : &ic->img[state];
			if (slot->present) return EF_ERR_CORRUPT;
			img.chunk = ch;
			img.chunklen = next - pos;
			*slot = img;
		}
		else if (!idis(ch, "PAD "))
		{
			if (ic->nunknown < EF_MAXUNKNOWN)
			{
				ic->unknown[ic->nunknown].data = ch;
				ic->unknown[ic->nunknown].len = next - pos;
				ic->nunknown++;
			}
		}
		pos = next;
	}
	if (!seenhead) return EF_ERR_CORRUPT;

	/* A selected image needs a normal one of the same kind; chunky images share one size. */
	if (ic->img[1].present)
	{
		const EFImage *a = &ic->img[0], *b = &ic->img[1];
		if (!a->present || a->kind != b->kind || a->width != b->width || a->height != b->height)
			return EF_ERR_CORRUPT;
	}
	if (ic->planar[1].present && !ic->planar[0].present) return EF_ERR_CORRUPT;
	return EF_OK;
}

int ef_parse_imag(const uint8_t *chunk, uint32_t len, EFImage *img, uint8_t *state)
{
	uint32_t clen;
	int r;
	if (len < 9 || !idis(chunk, "IMAG")) return EF_ERR_CORRUPT;
	clen = g32(chunk + 4);
	if (clen > len - 8 || chunk[8] > 1) return EF_ERR_CORRUPT;
	if ((r = parse_image(chunk + 8, clen, img)) != EF_OK) return r;
	img->chunk = chunk;
	img->chunklen = len;
	*state = chunk[8];
	return EF_OK;
}

int ef_image_unpack(const EFImage *img, uint8_t *dst, ef_uncompress_fn fn, void *ctx)
{
	if (!img->present) return EF_ERR_CORRUPT;
	if (img->comp == EF_RAW)
	{
		copybytes(dst, img->data, img->datalen);
		return EF_OK;
	}
	if (!fn || fn(ctx, dst, img->datalen, img->data, img->complen) != 0)
		return EF_ERR_UNPACK;
	return EF_OK;
}

static uint32_t image_hdrlen(const EFImage *img)
{
	uint32_t n = 8 + 4;
	if (img->kind == EF_CLUT) n += 4 + img->palsize * 3u;
	else if (img->kind == EF_PLANAR) n += 8;
	return n;
}

static uint32_t chunklen(uint32_t datalen) { return 8 + datalen + (datalen & 1); }

uint32_t ef_write_bound(const EFIcon *ic)
{
	uint32_t n = 12 + chunklen(24), i;
	if (ic->hasdrawer) n += chunklen(22);
	if (ic->deftool) n += chunklen(ic->deftoollen);
	if (ic->toolwindow) n += chunklen(ic->toolwindowlen);
	if (ic->tooltypes) n += chunklen(ic->tooltypeslen);
	if (ic->settings) n += chunklen(ic->settingslen);
	for (i = 0; i < 2; i++)
	{
		if (ic->img[i].present)
			n += chunklen(image_hdrlen(&ic->img[i]) + ic->img[i].datalen);
		if (ic->planar[i].present)
			n += chunklen(image_hdrlen(&ic->planar[i]) + ic->planar[i].datalen);
	}
	for (i = 0; i < ic->nunknown; i++)
		n += ic->unknown[i].len;
	return n + chunklen(EF_MINFILE);
}

static int put_chunk(uint8_t *dst, uint32_t dstmax, uint32_t *pos, const char *id,
                     const void *data, uint32_t len)
{
	uint32_t need = chunklen(len);
	if (dstmax - *pos < need) return EF_ERR_SPACE;
	copybytes(dst + *pos, (const uint8_t *)id, 4);
	p32(dst + *pos + 4, len);
	if (data) copybytes(dst + *pos + 8, data, len);
	else zerobytes(dst + *pos + 8, len);
	if (len & 1) dst[*pos + 8 + len] = 0;
	*pos += need;
	return EF_OK;
}

static int put_image(uint8_t *dst, uint32_t dstmax, uint32_t *pos, uint8_t state, const EFImage *img,
                     ef_compress_fn fn, void *ctx)
{
	uint32_t hdr = image_hdrlen(img), start = *pos, p, stored = img->datalen;
	uint8_t comp = EF_RAW, *h;

	if (ef_image_datalen(img) != img->datalen || !img->data) return EF_ERR_CORRUPT;
	if (dstmax - start < 8 + hdr + img->datalen + 1) return EF_ERR_SPACE;
	h = dst + start + 8;
	h[0] = state;
	h[1] = img->kind;
	h[3] = 0;
	p16(h + 4, img->width);
	p16(h + 6, img->height);
	p = 8;
	if (img->kind == EF_CLUT)
	{
		p16(h + p, img->palsize);
		p16(h + p + 2, (uint16_t)img->transparent);
		copybytes(h + p + 4, img->palette, img->palsize * 3u);
		p += 4 + img->palsize * 3u;
	}
	else if (img->kind == EF_PLANAR)
	{
		p16(h + p, (uint16_t)img->left);
		p16(h + p + 2, (uint16_t)img->top);
		p16(h + p + 4, img->depth);
		h[p + 6] = img->planepick;
		h[p + 7] = img->planeonoff;
		p += 8;
	}
	p32(h + p, img->datalen);
	p += 4;

	if (fn && img->datalen > 64)
	{
		uint32_t clen = img->datalen - 1;   /* only worth it if it gets smaller */
		if (fn(ctx, h + p, &clen, img->data, img->datalen) == 0 && clen > 0 && clen < img->datalen)
		{
			comp = EF_ZLIB;
			stored = clen;
		}
	}
	if (comp == EF_RAW)
		copybytes(h + p, img->data, img->datalen);
	h[2] = comp;

	copybytes(dst + start, (const uint8_t *)"IMAG", 4);
	p32(dst + start + 4, p + stored);
	*pos = start + chunklen(p + stored);
	if ((p + stored) & 1) dst[*pos - 1] = 0;
	return EF_OK;
}

int ef_write(const EFIcon *ic, uint8_t *dst, uint32_t dstmax, uint32_t *outlen,
             ef_compress_fn fn, void *ctx)
{
	uint8_t head[24], draw[22];
	uint32_t pos = 12, i;
	int r;

	if (dstmax < 12) return EF_ERR_SPACE;
	if (ic->tooltypes && ic->tooltypeslen && ic->tooltypes[ic->tooltypeslen - 1] != 0)
		return EF_ERR_CORRUPT;
	if (ic->settings && ic->settingslen && ic->settings[ic->settingslen - 1] != 0)
		return EF_ERR_CORRUPT;
	copybytes(dst, (const uint8_t *)"FORM", 4);
	copybytes(dst + 8, (const uint8_t *)"EMBL", 4);

	zerobytes(head, sizeof(head));
	p16(head, EF_VERSION);
	head[2] = ic->type;
	head[3] = ic->frameless ? 1 : 0;
	head[4] = ic->aspect;
	p16(head + 6, ic->gflags);
	p16(head + 8, ic->gwidth);
	p16(head + 10, ic->gheight);
	p32(head + 12, (uint32_t)ic->curx);
	p32(head + 16, (uint32_t)ic->cury);
	p32(head + 20, (uint32_t)ic->stack);
	if ((r = put_chunk(dst, dstmax, &pos, "HEAD", head, 24)) != EF_OK) return r;

	if (ic->hasdrawer)
	{
		p16(draw, (uint16_t)ic->dleft);
		p16(draw + 2, (uint16_t)ic->dtop);
		p16(draw + 4, (uint16_t)ic->dwidth);
		p16(draw + 6, (uint16_t)ic->dheight);
		p32(draw + 8, (uint32_t)ic->dcurx);
		p32(draw + 12, (uint32_t)ic->dcury);
		p32(draw + 16, ic->dflags);
		p16(draw + 20, ic->dviewmodes);
		if ((r = put_chunk(dst, dstmax, &pos, "DRAW", draw, 22)) != EF_OK) return r;
	}
	if (ic->deftool && (r = put_chunk(dst, dstmax, &pos, "DEFT", ic->deftool, ic->deftoollen)) != EF_OK)
		return r;
	if (ic->toolwindow && (r = put_chunk(dst, dstmax, &pos, "TWIN", ic->toolwindow, ic->toolwindowlen)) != EF_OK)
		return r;
	if (ic->tooltypes && (r = put_chunk(dst, dstmax, &pos, "TTYP", ic->tooltypes, ic->tooltypeslen)) != EF_OK)
		return r;
	if (ic->settings && (r = put_chunk(dst, dstmax, &pos, "ESET", ic->settings, ic->settingslen)) != EF_OK)
		return r;
	if (ic->img[1].present && !ic->img[0].present) return EF_ERR_CORRUPT;
	if (ic->planar[1].present && !ic->planar[0].present) return EF_ERR_CORRUPT;
	for (i = 0; i < 2; i++)
		if (ic->img[i].present && (ic->img[i].kind == EF_PLANAR
			|| (r = put_image(dst, dstmax, &pos, (uint8_t)i, &ic->img[i], fn, ctx)) != EF_OK))
			return ic->img[i].kind == EF_PLANAR ? EF_ERR_CORRUPT : r;
	for (i = 0; i < 2; i++)
		if (ic->planar[i].present && (ic->planar[i].kind != EF_PLANAR
			|| (r = put_image(dst, dstmax, &pos, (uint8_t)i, &ic->planar[i], fn, ctx)) != EF_OK))
			return ic->planar[i].kind != EF_PLANAR ? EF_ERR_CORRUPT : r;
	for (i = 0; i < ic->nunknown; i++)
	{
		if (dstmax - pos < ic->unknown[i].len) return EF_ERR_SPACE;
		copybytes(dst + pos, ic->unknown[i].data, ic->unknown[i].len);
		pos += ic->unknown[i].len;
	}
	if (pos < EF_MINFILE)
	{
		uint32_t padlen = pos + 8 >= EF_MINFILE ? 0 : EF_MINFILE - pos - 8;
		if ((r = put_chunk(dst, dstmax, &pos, "PAD ", 0, padlen)) != EF_OK) return r;
	}
	p32(dst + 4, pos - 8);
	*outlen = pos;
	return EF_OK;
}
