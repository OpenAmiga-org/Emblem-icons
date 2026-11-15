/* Host tests for src/png.c: every PngSuite image against the pypng reference
 * (build/pngref, from make_png_refs.py), corrupt x*.png images rejected,
 * bit flips and truncation never crash (ASan/UBSan). Build: make test */
#include "../../src/png.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL: "); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void *m_alloc(void *ctx, uint32_t n) { (void)ctx; return malloc(n ? n : 1); }
static void m_free(void *ctx, void *p) { (void)ctx; free(p); }
static const PngMem mem = { m_alloc, m_free, NULL };

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

static uint32_t rs = 777;
static uint32_t rnd(void) { rs = rs * 1103515245u + 12345u; return rs >> 8; }

int main(int argc, char **argv)
{
	const char *dir = argc > 1 ? argv[1] : "tests/samples/pngsuite";
	const char *refdir = argc > 2 ? argv[2] : "build/pngref";
	DIR *d = opendir(dir);
	struct dirent *e;
	int good = 0, bad = 0, fuzzed = 0;

	if (!d) { printf("no %s\n", dir); return 1; }
	while ((e = readdir(d)))
	{
		char path[512], ref[512];
		uint32_t len, w, h, rlen, k;
		uint8_t *buf, *argb, *rb;
		size_t n = strlen(e->d_name);
		int r;

		if (n < 5 || strcmp(e->d_name + n - 4, ".png")) continue;
		snprintf(path, sizeof(path), "%s/%s", dir, e->d_name);
		if (!(buf = readfile(path, &len))) continue;
		r = png_decode(buf, len, &mem, zu, NULL, &argb, &w, &h);

		if (e->d_name[0] == 'x')
		{
			CHECK(r != PNG_OK, "%s: corrupt image decoded", e->d_name);
			if (r == PNG_OK) free(argb);
			bad++;
		}
		else
		{
			snprintf(ref, sizeof(ref), "%s/%.*s.argb", refdir, (int)(n - 4), e->d_name);
			rb = readfile(ref, &rlen);
			CHECK(rb != NULL, "%s: no reference", e->d_name);
			CHECK(r == PNG_OK, "%s: decode error %d", e->d_name, r);
			if (rb && r == PNG_OK)
			{
				uint32_t rw = (uint32_t)rb[0] << 24 | rb[1] << 16 | rb[2] << 8 | rb[3];
				uint32_t rh = (uint32_t)rb[4] << 24 | rb[5] << 16 | rb[6] << 8 | rb[7];
				CHECK(rw == w && rh == h && rlen == 8 + w * h * 4, "%s: size %ux%u, ref %ux%u", e->d_name, w, h, rw, rh);
				if (rw == w && rh == h && rlen == 8 + w * h * 4)
				{
					uint32_t i;
					for (i = 0; i < w * h * 4 && argb[i] == rb[8 + i]; i++) ;
					CHECK(i == w * h * 4, "%s: pixel %u differs: got %02x%02x%02x%02x ref %02x%02x%02x%02x",
					      e->d_name, i / 4, argb[i & ~3u], argb[(i & ~3u) + 1], argb[(i & ~3u) + 2], argb[(i & ~3u) + 3],
					      rb[8 + (i & ~3u)], rb[9 + (i & ~3u)], rb[10 + (i & ~3u)], rb[11 + (i & ~3u)]);
				}
			}
			if (r == PNG_OK) free(argb);
			free(rb);
			good++;

			/* fuzz: bit flips (CRCs fixed up half of the time so the data path is reached) */
			for (k = 0; k < 40; k++)
			{
				uint8_t *b = malloc(len);
				uint32_t f, flips = 1 + rnd() % 3;
				memcpy(b, buf, len);
				for (f = 0; f < flips; f++) b[8 + rnd() % (len - 8)] ^= (uint8_t)(1u << (rnd() % 8));
				if (k & 1)
				{
					uint32_t pos = 8;
					while (pos + 12 <= len)
					{
						uint32_t cl = (uint32_t)b[pos] << 24 | b[pos + 1] << 16 | b[pos + 2] << 8 | b[pos + 3];
						uint32_t c;
						if (cl > len - pos - 12) break;
						c = png_crc32(0, b + pos + 4, cl + 4);
						b[pos + 8 + cl] = c >> 24; b[pos + 9 + cl] = c >> 16; b[pos + 10 + cl] = c >> 8; b[pos + 11 + cl] = c;
						pos += 12 + cl;
					}
				}
				if (png_decode(b, len, &mem, zu, NULL, &argb, &w, &h) == PNG_OK) free(argb);
				free(b);
				fuzzed++;
			}
			/* truncation */
			for (k = 0; k < len; k += 1 + len / 50)
				CHECK(png_decode(buf, k, &mem, zu, NULL, &argb, &w, &h) != PNG_OK, "%s: truncated at %u decoded", e->d_name, k);
		}
		free(buf);
	}
	closedir(d);
	printf("%s: %d failure(s); %d images checked, %d corrupt ones rejected, %d fuzzed decodes\n",
	       fails ? "FAILED" : "OK", fails, good, bad, fuzzed);
	return fails ? 1 : 0;
}
