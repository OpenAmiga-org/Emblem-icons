/* Host tests for src/emblemfile.c: random round trips, minimal icon,
 * unknown chunks, truncation and bit-flip fuzzing. Build: make test */
#include "../../src/emblemfile.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static uint32_t rs = 12345;
static uint32_t rnd(void) { rs = rs * 1103515245u + 12345u; return rs >> 8; }

static int zc(void *ctx, uint8_t *dst, uint32_t *dstlen, const uint8_t *src, uint32_t srclen)
{
	uLongf n = *dstlen;
	(void)ctx;
	if (compress2(dst, &n, src, srclen, 9) != Z_OK) return 1;
	*dstlen = (uint32_t)n;
	return 0;
}

static int zu(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen)
{
	uLongf n = dstlen;
	(void)ctx;
	if (uncompress(dst, &n, src, srclen) != Z_OK || n != dstlen) return 1;
	return 0;
}

static void rand_image(EFImage *img, int kind, uint16_t w, uint16_t h, int noisy)
{
	uint32_t i, n;
	uint8_t *d, *pal;
	memset(img, 0, sizeof(*img));
	img->present = 1;
	img->kind = (uint8_t)kind;
	img->width = w;
	img->height = h;
	img->transparent = -1;
	if (kind == EF_CLUT)
	{
		img->palsize = (uint16_t)(1 + rnd() % 256);
		img->transparent = (int16_t)((rnd() % 3) ? (int)(rnd() % img->palsize) : -1);
		pal = malloc(img->palsize * 3u);
		for (i = 0; i < img->palsize * 3u; i++) pal[i] = (uint8_t)rnd();
		img->palette = pal;
	}
	else if (kind == EF_PLANAR)
	{
		img->depth = (uint16_t)(1 + rnd() % 8);
		img->left = (int16_t)(rnd() % 5);
		img->top = (int16_t)(rnd() % 5);
		img->planepick = (uint8_t)((1u << img->depth) - 1);
		img->planeonoff = (uint8_t)(rnd() % 4);
	}
	n = ef_image_datalen(img);
	d = malloc(n);
	for (i = 0; i < n; i++) d[i] = noisy ? (uint8_t)rnd() : (uint8_t)((i / 7) & 0x0F);
	if (kind == EF_CLUT) for (i = 0; i < n; i++) d[i] %= img->palsize;
	img->data = d;
	img->datalen = n;
}

static char *rand_str(uint32_t *len)
{
	uint32_t n = rnd() % 40, i;
	char *s = malloc(n + 1);
	for (i = 0; i < n; i++) s[i] = (char)('a' + rnd() % 26);
	s[n] = 0;
	*len = n;
	return s;
}

static void free_icon(EFIcon *ic)
{
	int i;
	free((void *)ic->deftool);
	free((void *)ic->toolwindow);
	free((void *)ic->tooltypes);
	free((void *)ic->settings);
	for (i = 0; i < 2; i++)
	{
		free((void *)ic->img[i].data); free((void *)ic->img[i].palette);
		free((void *)ic->planar[i].data);
	}
}

static void rand_icon(EFIcon *ic)
{
	int kind = 1 + rnd() % 3;
	uint16_t w = (uint16_t)(1 + rnd() % (kind == EF_PLANAR ? 300 : 256));
	uint16_t h = (uint16_t)(1 + rnd() % 256);
	memset(ic, 0, sizeof(*ic));
	ic->type = (uint8_t)(1 + rnd() % 8);
	ic->frameless = (uint8_t)(rnd() & 1);
	ic->aspect = (uint8_t)rnd();
	ic->gflags = (uint16_t)rnd();
	ic->gwidth = w; ic->gheight = (uint16_t)(h + 1);
	ic->curx = (int32_t)(rnd() % 3 ? (int32_t)(rnd() % 2000) - 100 : (int32_t)0x80000000);
	ic->cury = (int32_t)(rnd() % 2000) - 100;
	ic->stack = (int32_t)rnd();
	if ((ic->hasdrawer = (uint8_t)(rnd() & 1)))
	{
		ic->dleft = (int16_t)rnd(); ic->dtop = (int16_t)rnd(); ic->dwidth = (int16_t)rnd(); ic->dheight = (int16_t)rnd();
		ic->dcurx = (int32_t)rnd(); ic->dcury = (int32_t)rnd(); ic->dflags = rnd(); ic->dviewmodes = (uint16_t)rnd();
	}
	if (rnd() & 1) ic->deftool = rand_str(&ic->deftoollen);
	if (rnd() & 1) ic->toolwindow = rand_str(&ic->toolwindowlen);
	if (rnd() % 4)
	{
		uint32_t n = rnd() % 6, i, l, pos = 0;
		char *tt = malloc(n * 41 + 1);
		for (i = 0; i < n; i++) { char *s = rand_str(&l); memcpy(tt + pos, s, l + 1); pos += l + 1; free(s); }
		ic->tooltypes = tt;
		ic->tooltypeslen = pos;
	}
	if (rnd() % 3)
	{
		uint32_t n = rnd() % 5, i, l, pos = 0;
		char *es = malloc(n * 41 + 1);
		for (i = 0; i < n; i++) { char *s = rand_str(&l); memcpy(es + pos, s, l + 1); pos += l + 1; free(s); }
		ic->settings = es;
		ic->settingslen = pos;
	}
	if (rnd() % 8)
	{
		if (kind == EF_PLANAR)
		{
			rand_image(&ic->planar[0], kind, w, h, rnd() & 1);
			if (rnd() & 1)
				rand_image(&ic->planar[1], kind, (uint16_t)(1 + rnd() % 64), (uint16_t)(1 + rnd() % 64), rnd() & 1);
		}
		else
		{
			rand_image(&ic->img[0], kind, w, h, rnd() & 1);
			if (rnd() & 1) rand_image(&ic->img[1], kind, w, h, rnd() & 1);
			if (rnd() & 1)   /* planar fallback of a chunky icon */
			{
				rand_image(&ic->planar[0], EF_PLANAR, (uint16_t)(1 + rnd() % 80), (uint16_t)(1 + rnd() % 80), 0);
				if (rnd() & 1)
					rand_image(&ic->planar[1], EF_PLANAR, ic->planar[0].width, ic->planar[0].height, 1);
			}
		}
	}
}

static int same_str(const char *a, uint32_t al, const char *b, uint32_t bl)
{
	if (!a || !b) return !a && !b;
	return al == bl && memcmp(a, b, al) == 0;
}

static void compare(const EFIcon *a, const EFIcon *b, const char *what)
{
	int i;
	CHECK(a->type == b->type && a->frameless == b->frameless && a->aspect == b->aspect, "%s head", what);
	CHECK(a->gflags == b->gflags && a->gwidth == b->gwidth && a->gheight == b->gheight, "%s gadget", what);
	CHECK(a->curx == b->curx && a->cury == b->cury && a->stack == b->stack, "%s pos/stack", what);
	CHECK(a->hasdrawer == b->hasdrawer, "%s hasdrawer", what);
	if (a->hasdrawer && b->hasdrawer)
		CHECK(a->dleft == b->dleft && a->dtop == b->dtop && a->dwidth == b->dwidth && a->dheight == b->dheight
		      && a->dcurx == b->dcurx && a->dcury == b->dcury && a->dflags == b->dflags
		      && a->dviewmodes == b->dviewmodes, "%s drawer", what);
	CHECK(same_str(a->deftool, a->deftoollen, b->deftool, b->deftoollen), "%s deftool", what);
	CHECK(same_str(a->toolwindow, a->toolwindowlen, b->toolwindow, b->toolwindowlen), "%s toolwindow", what);
	CHECK(same_str(a->tooltypes, a->tooltypeslen, b->tooltypes, b->tooltypeslen), "%s tooltypes", what);
	CHECK(same_str(a->settings, a->settingslen, b->settings, b->settingslen), "%s settings", what);
	for (i = 0; i < 4; i++)
	{
		const EFImage *x = i < 2 ? &a->img[i] : &a->planar[i - 2], *y = i < 2 ? &b->img[i] : &b->planar[i - 2];
		CHECK(x->present == y->present, "%s img%d present", what, i);
		if (!x->present || !y->present) continue;
		CHECK(x->kind == y->kind && x->width == y->width && x->height == y->height, "%s img%d dims", what, i);
		if (x->kind == EF_CLUT)
			CHECK(x->palsize == y->palsize && x->transparent == y->transparent
			      && memcmp(x->palette, y->palette, x->palsize * 3u) == 0, "%s img%d palette", what, i);
		if (x->kind == EF_PLANAR)
			CHECK(x->left == y->left && x->top == y->top && x->depth == y->depth
			      && x->planepick == y->planepick && x->planeonoff == y->planeonoff, "%s img%d planar", what, i);
		CHECK(x->datalen == y->datalen, "%s img%d datalen", what, i);
		if (x->datalen == y->datalen)
		{
			uint8_t *u = malloc(y->datalen);
			CHECK(ef_image_unpack(y, u, zu, NULL) == EF_OK, "%s img%d unpack", what, i);
			CHECK(memcmp(u, x->data, x->datalen) == 0, "%s img%d pixels", what, i);
			free(u);
		}
	}
}

/* Every prefix and many corrupted copies must parse without touching memory
 * outside the buffer; unpack must never write past datalen. */
static void fuzz(const uint8_t *file, uint32_t len)
{
	uint32_t cut, k;
	for (cut = 0; cut < len; cut += (len > 4000 ? 97 : 1))
	{
		uint8_t *b = malloc(cut ? cut : 1);
		EFIcon ic;
		memcpy(b, file, cut);
		CHECK(ef_parse(b, cut, &ic) != EF_OK, "truncated file at %u/%u parsed", cut, len);
		free(b);
	}
	for (k = 0; k < 300; k++)
	{
		uint8_t *b = malloc(len);
		EFIcon ic;
		uint32_t flips = 1 + rnd() % 4, f;
		memcpy(b, file, len);
		for (f = 0; f < flips; f++) b[rnd() % len] ^= (uint8_t)(1u << (rnd() % 8));
		if (ef_parse(b, len, &ic) == EF_OK)
		{
			int i;
			for (i = 0; i < 4; i++)
			{
				EFImage *im = i < 2 ? &ic.img[i] : &ic.planar[i - 2];
				if (im->present)
				{
					uint8_t *u = malloc(im->datalen);
					ef_image_unpack(im, u, zu, NULL);
					free(u);
				}
			}
		}
		free(b);
	}
}

int main(void)
{
	int n;
	uint32_t total = 0, totalraw = 0;

	for (n = 0; n < 400; n++)
	{
		EFIcon a, b;
		uint32_t bound, len;
		uint8_t *buf;
		int usez = n % 3 != 0, r;
		char what[32];

		snprintf(what, sizeof(what), "icon %d", n);
		rand_icon(&a);
		bound = ef_write_bound(&a);
		buf = malloc(bound);
		r = ef_write(&a, buf, bound, &len, usez ? zc : NULL, NULL);
		CHECK(r == EF_OK, "%s write %d", what, r);
		if (r == EF_OK)
		{
			CHECK(len >= EF_MINFILE, "%s short file %u", what, len);
			CHECK(len <= bound, "%s over bound", what);
			CHECK(ef_is_emblem(buf, len) && ef_file_size(buf, len) == len, "%s magic/size", what);
			r = ef_parse(buf, len, &b);
			CHECK(r == EF_OK, "%s parse %d", what, r);
			if (r == EF_OK) compare(&a, &b, what);
			/* every IMAG chunk parses alone the same (ef_parse_imag) */
			if (r == EF_OK)
			{
				int i;
				for (i = 0; i < 4; i++)
				{
					const EFImage *x = i < 2 ? &b.img[i] : &b.planar[i - 2];
					EFImage y;
					uint8_t st = 9;
					if (!x->present) continue;
					CHECK(ef_parse_imag(x->chunk, x->chunklen, &y, &st) == EF_OK && st == (i & 1)
					      && y.kind == x->kind && y.width == x->width && y.height == x->height
					      && y.datalen == x->datalen && y.data == x->data && y.complen == x->complen,
					      "%s imag %d alone", what, i);
				}
				CHECK(ef_parse_imag(buf, len, &(EFImage){0}, &(uint8_t){0}) != EF_OK, "%s FORM is no IMAG", what);
			}
			/* the snapshot position is where the format says */
			CHECK(buf[EF_POSOFFSET] == (uint8_t)((uint32_t)a.curx >> 24)
			      && buf[EF_POSOFFSET + 7] == (uint8_t)a.cury, "%s position offset", what);
			total += len;
			totalraw += a.img[0].datalen + a.img[1].datalen + a.planar[0].datalen + a.planar[1].datalen;
			if (n < 60) fuzz(buf, len);
			/* too small a buffer fails cleanly */
			CHECK(ef_write(&a, buf, len - 1, &len, usez ? zc : NULL, NULL) == EF_ERR_SPACE, "%s space", what);
		}
		free(buf);
		free_icon(&a);
	}

	/* minimal icon: no images, no strings, still >= 58 bytes */
	{
		EFIcon a, b;
		uint8_t buf[256];
		uint32_t len;
		memset(&a, 0, sizeof(a));
		a.type = 3;
		CHECK(ef_write(&a, buf, sizeof(buf), &len, NULL, NULL) == EF_OK && len >= EF_MINFILE, "minimal write");
		CHECK(ef_parse(buf, len, &b) == EF_OK && b.type == 3 && !b.img[0].present, "minimal parse");
	}

	/* unknown chunk survives parse -> write -> parse */
	{
		EFIcon a, b, c;
		uint8_t buf[512], buf2[512], extra[] = { 'X', 'T', 'R', 'A', 0, 0, 0, 3, 1, 2, 3, 0 };
		uint32_t len, len2;
		memset(&a, 0, sizeof(a));
		a.type = 1;
		a.unknown[0].data = extra;
		a.unknown[0].len = sizeof(extra);
		a.nunknown = 1;
		CHECK(ef_write(&a, buf, sizeof(buf), &len, NULL, NULL) == EF_OK, "unknown write");
		CHECK(ef_parse(buf, len, &b) == EF_OK && b.nunknown == 1 && b.unknown[0].len == sizeof(extra)
		      && memcmp(b.unknown[0].data, extra, sizeof(extra)) == 0, "unknown parse");
		CHECK(ef_write(&b, buf2, sizeof(buf2), &len2, NULL, NULL) == EF_OK && len2 == len
		      && memcmp(buf, buf2, len) == 0, "unknown rewrite identical");
		CHECK(ef_parse(buf2, len2, &c) == EF_OK && c.nunknown == 1, "unknown reparse");
	}

	/* settings (ESET): written, read back, checked like the tool types */
	{
		EFIcon a, b;
		uint8_t buf[512], buf2[600];
		const char es[] = "IMAGE=Drawer\0EMBLEM=INTERNAL,30,30,33,30,SHADOW";
		const char tt[] = "DONOTWAIT";
		uint32_t len, pos;
		memset(&a, 0, sizeof(a));
		a.type = 2;
		a.tooltypes = tt;
		a.tooltypeslen = sizeof(tt);
		a.settings = es;
		a.settingslen = sizeof(es);
		CHECK(ef_write(&a, buf, sizeof(buf), &len, NULL, NULL) == EF_OK, "settings write");
		CHECK(ef_parse(buf, len, &b) == EF_OK && b.settingslen == sizeof(es)
		      && memcmp(b.settings, es, sizeof(es)) == 0 && ef_count_tooltypes(b.settings, b.settingslen) == 2
		      && b.tooltypeslen == sizeof(tt) && b.nunknown == 0, "settings parse");
		/* not NUL-terminated: refused on writing */
		a.settingslen = sizeof(es) - 1;
		CHECK(ef_write(&a, buf2, sizeof(buf2), &len, NULL, NULL) == EF_ERR_CORRUPT, "settings unterminated");
		/* two ESET chunks: corrupt */
		a.settingslen = sizeof(es);
		CHECK(ef_write(&a, buf, sizeof(buf), &len, NULL, NULL) == EF_OK, "settings write 2");
		for (pos = 12; pos + 8 <= len && memcmp(buf + pos, "ESET", 4) != 0; )
			pos += 8 + (((buf[pos + 4] << 24 | buf[pos + 5] << 16 | buf[pos + 6] << 8 | buf[pos + 7]) + 1u) & ~1u);
		CHECK(pos + 8 <= len, "settings chunk found");
		if (pos + 8 <= len)
		{
			uint32_t clen = 8 + ((sizeof(es) + 1u) & ~1u), total;
			memcpy(buf2, buf, len);
			memcpy(buf2 + len, buf + pos, clen);
			total = len + clen - 8;
			buf2[4] = (uint8_t)(total >> 24); buf2[5] = (uint8_t)(total >> 16);
			buf2[6] = (uint8_t)(total >> 8); buf2[7] = (uint8_t)total;
			CHECK(ef_parse(buf2, len + clen, &b) == EF_ERR_CORRUPT, "two settings chunks");
		}
	}

	/* not an Emblem file: native icon magic, PNG */
	{
		uint8_t native[64] = { 0xE3, 0x10, 0, 1 }, png[64] = { 0x89, 'P', 'N', 'G' };
		EFIcon ic;
		CHECK(ef_parse(native, sizeof(native), &ic) == EF_ERR_NOTEMBLEM, "native rejected");
		CHECK(ef_parse(png, sizeof(png), &ic) == EF_ERR_NOTEMBLEM, "png rejected");
	}

	printf("%s: %d failure(s); 400 icons, %u bytes written for %u bytes of pixels\n",
	       fails ? "FAILED" : "OK", fails, total, totalraw);
	return fails ? 1 : 0;
}
