/*
 * mkemblem - write an Emblem icon file on the host (for the package's
 * example icons). Uses the same codec as emblem.iconmodule.
 *
 *   mkemblem OUT.info TYPE=DRAWER|PROJECT|TOOL|DISK|GARBAGE IMAGE=normal.png
 *            [SELECTED=selected.png] [TOOL=default tool] [STACK=n] [POS=x,y]
 *            [WINDOW=x,y,w,h] [TT=tool type]...
 *
 * The icon's own images are the PNGs (32-bit ARGB). No planar fallback is
 * stored: the module builds one when it loads the icon.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

#include "../src/emblemfile.h"
#include "../src/png.h"

#define NO_ICON_POSITION 0x80000000UL

static void *m_alloc(void *ctx, uint32_t n) { (void)ctx; return malloc(n ? n : 1); }
static void m_free(void *ctx, void *p) { (void)ctx; free(p); }
static const PngMem pmem = { m_alloc, m_free, NULL };

static int zu(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen)
{
	uLongf n = dstlen;
	(void)ctx;
	return uncompress(dst, &n, src, srclen) == Z_OK && n == dstlen ? 0 : 1;
}

static int zc(void *ctx, uint8_t *dst, uint32_t *dstlen, const uint8_t *src, uint32_t srclen)
{
	uLongf n = *dstlen;
	(void)ctx;
	if (compress2(dst, &n, src, srclen, 9) != Z_OK) return 1;
	*dstlen = (uint32_t)n;
	return 0;
}

static void die(const char *msg, const char *arg)
{
	fprintf(stderr, "mkemblem: %s%s\n", msg, arg ? arg : "");
	exit(10);
}

static void load_png(const char *path, EFImage *img)
{
	FILE *f = fopen(path, "rb");
	uint8_t *buf, *argb;
	uint32_t w, h;
	long n;
	if (!f) die("cannot open ", path);
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	buf = malloc(n);
	if (fread(buf, 1, n, f) != (size_t)n) die("cannot read ", path);
	fclose(f);
	if (png_decode(buf, (uint32_t)n, &pmem, zu, NULL, &argb, &w, &h) != PNG_OK) die("not a usable PNG: ", path);
	free(buf);
	if (w > EF_MAXDIM || h > EF_MAXDIM) die("image larger than 256x256: ", path);
	memset(img, 0, sizeof(*img));
	img->present = 1;
	img->kind = EF_ARGB;
	img->width = (uint16_t)w;
	img->height = (uint16_t)h;
	img->transparent = -1;
	img->data = argb;
	img->datalen = w * h * 4;
}

int main(int argc, char **argv)
{
	EFIcon ic;
	char tts[8192];
	uint32_t ttlen = 0, len;
	uint8_t *out;
	FILE *f;
	int i;

	if (argc < 3) die("usage: mkemblem OUT.info TYPE=... IMAGE=file.png [SELECTED=] [TOOL=] [STACK=] [POS=x,y] [WINDOW=x,y,w,h] [TT=]...", NULL);
	memset(&ic, 0, sizeof(ic));
	ic.type = 0;
	ic.frameless = 1;
	ic.curx = ic.cury = (int32_t)NO_ICON_POSITION;
	for (i = 2; i < argc; i++)
	{
		const char *a = argv[i];
		if (!strncmp(a, "TYPE=", 5))
		{
			static const char *const names[] = { "", "DISK", "DRAWER", "TOOL", "PROJECT", "GARBAGE" };
			for (int k = 1; k <= 5; k++)
				if (!strcmp(a + 5, names[k])) ic.type = (uint8_t)k;
		}
		else if (!strncmp(a, "IMAGE=", 6)) load_png(a + 6, &ic.img[0]);
		else if (!strncmp(a, "SELECTED=", 9)) load_png(a + 9, &ic.img[1]);
		else if (!strncmp(a, "TOOL=", 5)) { ic.deftool = a + 5; ic.deftoollen = (uint32_t)strlen(a + 5); }
		else if (!strncmp(a, "STACK=", 6)) ic.stack = atoi(a + 6);
		else if (!strncmp(a, "POS=", 4))
		{
			if (sscanf(a + 4, "%d,%d", &ic.curx, &ic.cury) != 2) die("bad ", a);
		}
		else if (!strncmp(a, "WINDOW=", 7))
		{
			int x, y, w, h;
			if (sscanf(a + 7, "%d,%d,%d,%d", &x, &y, &w, &h) != 4) die("bad ", a);
			ic.hasdrawer = 1;
			ic.dleft = (int16_t)x; ic.dtop = (int16_t)y; ic.dwidth = (int16_t)w; ic.dheight = (int16_t)h;
		}
		else if (!strncmp(a, "TT=", 3))
		{
			size_t n = strlen(a + 3) + 1;
			if (ttlen + n > sizeof(tts)) die("too many tool types", NULL);
			memcpy(tts + ttlen, a + 3, n);
			ttlen += (uint32_t)n;
		}
		else die("unknown argument ", a);
	}
	if (!ic.type) die("TYPE= missing or unknown", NULL);
	if (!ic.img[0].present) die("IMAGE= missing", NULL);
	if (ic.img[1].present && (ic.img[1].width != ic.img[0].width || ic.img[1].height != ic.img[0].height))
		die("SELECTED= must have the size of IMAGE=", NULL);
	if (ttlen)
	{
		ic.tooltypes = tts;
		ic.tooltypeslen = ttlen;
	}
	ic.gwidth = ic.img[0].width;
	ic.gheight = ic.img[0].height;
	ic.gflags = ic.img[1].present ? 0x0006 : 0x0004;   /* GADGIMAGE (+ GADGHIMAGE) */

	len = ef_write_bound(&ic);
	out = malloc(len);
	if (ef_write(&ic, out, len, &len, zc, NULL) != EF_OK) die("ef_write failed", NULL);

	/* the written file must parse back */
	{
		EFIcon chk;
		if (ef_parse(out, len, &chk) != EF_OK || chk.type != ic.type) die("written file does not parse", NULL);
	}
	if (!(f = fopen(argv[1], "wb")) || fwrite(out, 1, len, f) != len || fclose(f)) die("cannot write ", argv[1]);
	free(out);
	free((void *)ic.img[0].data);
	free((void *)ic.img[1].data);
	return 0;
}
