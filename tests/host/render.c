/*
 * render - compose an icon on the host exactly like emblem.iconmodule does
 * (same PNG decoder, same integer composition), for golden renders and for
 * the expected pixels of the guest tests.
 *
 *   render [--dir DIR] [--own1 FILE] [--own2 FILE] [--prefs FILE] [--out PREFIX] TOOLTYPE...
 *
 * --dir    folder of the default images and emblems (Name -> DIR/Name.png)
 * --own1/2 the icon's own normal/selected image: .argb (u32 w, u32 h, A,R,G,B
 *          bytes; what "icontest pixels" writes) or .png
 * --prefs  settings file (emblem.prefs); default: the built-in settings
 * --ttfile tool types from a file, one per line (before the TOOLTYPE arguments)
 * --out    write PREFIX_1.png and PREFIX_2.png
 * Prints "composed=1 size=WxH img1=CRC img2=CRC" or "composed=0".
 */
#include "../../src/compose.h"
#include "../../src/emblemspec.h"
#include "../../src/png.h"
#include "../../src/emblemprefs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

static void *m_alloc(void *ctx, uint32_t n) { (void)ctx; return malloc(n ? n : 1); }
static void m_free(void *ctx, void *p) { (void)ctx; free(p); }
static const CPMem mem = { m_alloc, m_free, NULL };
static const PngMem pmem = { m_alloc, m_free, NULL };

static int zu(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen)
{
	uLongf n = dstlen;
	(void)ctx;
	return uncompress(dst, &n, src, srclen) == Z_OK && n == dstlen ? 0 : 1;
}

static uint8_t *readfile(const char *path, uint32_t *len)
{
	FILE *f = fopen(path, "rb");
	uint8_t *b;
	long n;
	if (!f) return NULL;
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	b = malloc(n ? n : 1);
	if (fread(b, 1, n, f) != (size_t)n) { free(b); fclose(f); return NULL; }
	fclose(f);
	*len = (uint32_t)n;
	return b;
}

static int load_image(const char *path, CPImage *img)
{
	uint32_t len, w, h;
	uint8_t *b = readfile(path, &len), *argb;
	size_t n = strlen(path);
	if (!b) return 0;
	if (n > 5 && !strcmp(path + n - 5, ".argb"))
	{
		if (len < 8) { free(b); return 0; }
		w = (uint32_t)b[0] << 24 | b[1] << 16 | b[2] << 8 | b[3];
		h = (uint32_t)b[4] << 24 | b[5] << 16 | b[6] << 8 | b[7];
		if (len != 8 + w * h * 4) { free(b); return 0; }
		argb = malloc(w * h * 4);
		memcpy(argb, b + 8, w * h * 4);
	}
	else if (len > 2 * 1024 * 1024 || png_decode(b, len, &pmem, zu, NULL, &argb, &w, &h) != PNG_OK)
	{
		free(b);
		return 0;
	}
	free(b);
	img->px = argb;
	img->w = w;
	img->h = h;
	return 1;
}

static const char *dir = ".";
static CPImage own[2];
static CPImage cache[16];
static char cachename[16][ES_NAMELEN];
static int ncache;

static int get(void *ctx, const char *name, int o, CPImage *img)
{
	char path[1024];
	const char *base, *p;
	int ext = 0, i;
	(void)ctx;
	if (!name)
	{
		if (!own[o].px) return 0;
		*img = own[o];
		return 1;
	}
	for (i = 0; i < ncache; i++)
		if (!strcasecmp(cachename[i], name)) { *img = cache[i]; return cache[i].px != NULL; }
	base = strrchr(name, '/') ? strrchr(name, '/') + 1 : name;
	for (p = base; *p; p++) if (*p == '.') ext = 1;
	snprintf(path, sizeof(path), "%s/%s%s", dir, name, ext ? "" : ".png");
	if (ncache < 16)
	{
		strcpy(cachename[ncache], name);
		cache[ncache].px = NULL;
		load_image(path, &cache[ncache]);
		*img = cache[ncache];
		return cache[ncache++].px != NULL;
	}
	return 0;
}

static void write_png(const char *path, const uint8_t *argb, uint32_t w, uint32_t h)
{
	uint32_t rowlen = 1 + w * 4, i, x, y;
	uint8_t *raw = malloc(rowlen * h), *z;
	uLongf zlen = compressBound(rowlen * h);
	FILE *f = fopen(path, "wb");
	static const uint8_t sig[8] = { 0x89, 'P', 'N', 'G', 13, 10, 26, 10 };
	uint8_t ihdr[13] = { w >> 24, w >> 16, w >> 8, w, h >> 24, h >> 16, h >> 8, h, 8, 6, 0, 0, 0 };
	if (!f) { free(raw); return; }
	for (y = 0; y < h; y++)
	{
		raw[y * rowlen] = 0;
		for (x = 0; x < w; x++)
		{
			const uint8_t *s = argb + (y * w + x) * 4;
			uint8_t *d = raw + y * rowlen + 1 + x * 4;
			d[0] = s[1]; d[1] = s[2]; d[2] = s[3]; d[3] = s[0];
		}
	}
	z = malloc(zlen);
	compress2(z, &zlen, raw, rowlen * h, 9);
	fwrite(sig, 1, 8, f);
	{
		struct { const char *id; const uint8_t *d; uint32_t n; } ch[3] = { { "IHDR", ihdr, 13 }, { "IDAT", z, (uint32_t)zlen }, { "IEND", NULL, 0 } };
		for (i = 0; i < 3; i++)
		{
			uint8_t hdr[8] = { ch[i].n >> 24, ch[i].n >> 16, ch[i].n >> 8, ch[i].n, 0, 0, 0, 0 };
			uint32_t crc;
			memcpy(hdr + 4, ch[i].id, 4);
			fwrite(hdr, 1, 8, f);
			if (ch[i].n) fwrite(ch[i].d, 1, ch[i].n, f);
			crc = png_crc32(0, hdr + 4, 4);
			if (ch[i].n) crc = png_crc32(crc, ch[i].d, ch[i].n);
			{
				uint8_t c[4] = { crc >> 24, crc >> 16, crc >> 8, crc };
				fwrite(c, 1, 4, f);
			}
		}
	}
	fclose(f);
	free(raw);
	free(z);
}

int main(int argc, char **argv)
{
	static char tt[1024 * 1024 + 2];
	uint32_t n = 0;
	const char *out = NULL;
	ESpec spec;
	CPResult res;
	CPPrefs prefs;
	int i, r;

	ep_defaults(&prefs);

	for (i = 1; i < argc; i++)
	{
		if (!strcmp(argv[i], "--dir") && i + 1 < argc) dir = argv[++i];
		else if (!strcmp(argv[i], "--own1") && i + 1 < argc) { if (!load_image(argv[++i], &own[0])) { fprintf(stderr, "can't read %s\n", argv[i]); return 20; } }
		else if (!strcmp(argv[i], "--own2") && i + 1 < argc) { if (!load_image(argv[++i], &own[1])) { fprintf(stderr, "can't read %s\n", argv[i]); return 20; } }
		else if (!strcmp(argv[i], "--out") && i + 1 < argc) out = argv[++i];
		else if (!strcmp(argv[i], "--ttfile") && i + 1 < argc)
		{
			/* tool types, one per line (as "icontest ttfile" sets them) */
			uint32_t len, k;
			uint8_t *t = readfile(argv[++i], &len);
			if (!t) { fprintf(stderr, "can't read %s\n", argv[i]); return 20; }
			for (k = 0; k < len && n < sizeof(tt) - 1; k++) tt[n++] = t[k] == '\n' ? 0 : (char)t[k];
			if (n && tt[n - 1]) tt[n++] = 0;
			free(t);
		}
		else if (!strcmp(argv[i], "--prefs") && i + 1 < argc)
		{
			uint32_t len;
			uint8_t *t = readfile(argv[++i], &len);
			if (!t) { fprintf(stderr, "can't read %s\n", argv[i]); return 20; }
			ep_parse((const char *)t, len > EP_MAXFILE ? EP_MAXFILE : len, &prefs);
			free(t);
		}
		else if (n + strlen(argv[i]) + 1 < sizeof(tt))
		{
			strcpy(tt + n, argv[i]);
			n += (uint32_t)strlen(argv[i]) + 1;
		}
	}
	es_parse(tt, n, &spec);
	r = cp_compose(&spec, &prefs, get, NULL, &mem, &mem, NULL, &res);
	if (r != 1)
	{
		printf("composed=0\n");
		return r < 0 ? 10 : 0;
	}
	printf("composed=1 size=%ux%u img1=%08lX", res.w, res.h, crc32(0, res.img[0], res.w * res.h * 4));
	if (res.img[1]) printf(" img2=%08lX", crc32(0, res.img[1], res.w * res.h * 4));
	printf("\n");
	if (out)
	{
		char path[1024];
		for (i = 0; i < 2; i++)
			if (res.img[i])
			{
				snprintf(path, sizeof(path), "%s_%d.png", out, i + 1);
				write_png(path, res.img[i], res.w, res.h);
			}
	}
	return 0;
}
