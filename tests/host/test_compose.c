/* Host tests for the composition engine in src/compose.c. Build: make test */
#include "../../src/compose.h"
#include "../../src/emblemspec.h"
#include "../../src/emblemprefs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static int failafter = -1;   /* make the n-th allocation fail */
static void *m_alloc(void *ctx, uint32_t n)
{
	(void)ctx;
	if (failafter == 0) return NULL;
	if (failafter > 0) failafter--;
	return malloc(n ? n : 1);
}
static void m_free(void *ctx, void *p) { (void)ctx; free(p); }
static const CPMem mem = { m_alloc, m_free, NULL };

static uint8_t *solid(uint32_t w, uint32_t h, uint8_t a, uint8_t r, uint8_t g, uint8_t b)
{
	uint8_t *p = malloc(w * h * 4);
	for (uint32_t i = 0; i < w * h; i++) { p[i * 4] = a; p[i * 4 + 1] = r; p[i * 4 + 2] = g; p[i * 4 + 3] = b; }
	return p;
}
static const uint8_t *px(const uint8_t *img, uint32_t w, uint32_t x, uint32_t y) { return img + (y * w + x) * 4; }
static int is(const uint8_t *p, int a, int r, int g, int b) { return p[0] == a && p[1] == r && p[2] == g && p[3] == b; }

/* image source for cp_compose: a few named images and the icon's own two */
static CPImage own[2], named[6];
static const char *names[6] = { "Base", "Sel", "Emb", "Huge", "Margin", "Big" };
static CPPrefs prefs;
static int get(void *ctx, const char *name, int o, CPImage *img)
{
	(void)ctx;
	if (!name) { if (!own[o].px) return 0; *img = own[o]; return 1; }
	for (int i = 0; i < 6; i++)
		if (!strcmp(name, names[i]) && named[i].px) { *img = named[i]; return 1; }
	return 0;
}

/* a scaled-emblem cache for the tests: results must be the same with and without it */
static int usecache = 0, finds = 0, hits = 0, stores = 0;
static struct { char name[64]; uint32_t w, h; uint8_t *px; } sc[32];
static int nsc;
static const uint8_t *sc_find(void *ctx, const char *name, uint32_t w, uint32_t h)
{
	(void)ctx;
	finds++;
	for (int i = 0; i < nsc; i++)
		if (!strcmp(sc[i].name, name) && sc[i].w == w && sc[i].h == h) { hits++; return sc[i].px; }
	return NULL;
}
static void sc_store(void *ctx, const char *name, uint32_t w, uint32_t h, const uint8_t *px)
{
	(void)ctx;
	stores++;
	if (nsc >= 32) return;
	strcpy(sc[nsc].name, name);
	sc[nsc].w = w; sc[nsc].h = h;
	sc[nsc].px = malloc(w * h * 4);
	memcpy(sc[nsc].px, px, w * h * 4);
	nsc++;
}
static const CPScaleCache scache = { sc_find, sc_store, NULL };

static int compose(const char *const *tt, CPResult *res)
{
	char buf[1024];
	uint32_t n = 0;
	ESpec spec;
	for (; *tt; tt++) { strcpy(buf + n, *tt); n += (uint32_t)strlen(*tt) + 1; }
	es_parse(buf, n, &spec);
	return cp_compose(&spec, &prefs, get, NULL, &mem, &mem, usecache ? &scache : NULL, res);
}
static void freeres(CPResult *r) { free(r->img[0]); free(r->img[1]); r->img[0] = r->img[1] = NULL; }

static const char *prefstext;
static int parse_prefs(const char *t) { prefstext = t; ep_defaults(&prefs); return ep_parse(t, (uint32_t)strlen(t), &prefs); }

int main(void)
{
	ep_defaults(&prefs);
	/* --- prefs file */
	{
		CHECK(prefs.imagemethod == ES_NONE && prefs.emblemmethod == ES_NONE && prefs.shadowx == 5 && prefs.shadowy == 5
		      && prefs.shadowblur == 2 && prefs.shadowopacity == 50 && prefs.glowsize == 2 && prefs.glowopacity == 80
		      && prefs.glowrgb[0] == 255, "defaults");
		CHECK(parse_prefs("METHOD=SHADOW\n") == 1 && prefs.imagemethod == ES_SHADOW && prefs.emblemmethod == ES_SHADOW, "METHOD");
		CHECK(parse_prefs("emblemmethod = glow\r\nMETHOD=DARK\r\n") == 2 && prefs.imagemethod == ES_DARK
		      && prefs.emblemmethod == ES_GLOW, "specific key wins, CRLF, case, spaces");
		CHECK(parse_prefs("# comment\n;METHOD=GLOW\nIMAGEMETHOD=BRIGHT") == 1 && prefs.imagemethod == ES_BRIGHT
		      && prefs.emblemmethod == ES_NONE, "comments, last line without newline");
		CHECK(parse_prefs("SHADOWOFFSET=3,-2\nSHADOWBLUR=0\nSHADOWOPACITY=100\nGLOWSIZE=8\nGLOWOPACITY=0\nGLOWCOLOR=#FF8000") == 6
		      && prefs.shadowx == 3 && prefs.shadowy == -2 && prefs.shadowblur == 0 && prefs.shadowopacity == 100
		      && prefs.glowsize == 8 && prefs.glowopacity == 0 && prefs.glowrgb[0] == 255 && prefs.glowrgb[1] == 128
		      && prefs.glowrgb[2] == 0, "all settings");
		CHECK(parse_prefs("SHADOWOFFSET=4\nGLOWCOLOR=0x0000ff") == 2 && prefs.shadowx == 4 && prefs.shadowy == 4
		      && prefs.glowrgb[2] == 255, "one offset, 0x colour");
		CHECK(parse_prefs("METHOD=WOBBLE\nMETHOD=\nSHADOWBLUR=9\nSHADOWOFFSET=17,0\nGLOWSIZE=0\nSHADOWOPACITY=101\n"
		                  "GLOWCOLOR=12345\nGLOWCOLOR=GGGGGG\nNOKEY\n=5\nSHADOWBLUR=1x\n") == 0
		      && prefs.shadowblur == 2 && prefs.shadowx == 5 && prefs.glowsize == 2, "bad values ignored");
		(void)prefstext;
		ep_defaults(&prefs);
	}
	/* --- methods */
	{
		uint8_t p[8] = { 255, 200, 100, 0, 0, 0, 0, 0 };
		cp_method(p, 1, ES_DARK);
		CHECK(is(p, 255, 150, 75, 0), "dark %d %d %d", p[1], p[2], p[3]);
		uint8_t q[4] = { 255, 0, 100, 255 };
		cp_method(q, 1, ES_BRIGHT);
		CHECK(is(q, 255, 64, 139, 255), "bright %d %d %d", q[1], q[2], q[3]);
		uint8_t r[4] = { 128, 255, 0, 0 };
		cp_method(r, 1, ES_GRAY);
		CHECK(r[0] == 128 && r[1] == r[2] && r[2] == r[3] && r[1] == 77, "gray %d", r[1]);
		uint8_t s[4] = { 255, 1, 2, 3 };
		cp_method(s, 1, ES_NONE); cp_method(s, 1, ES_SHADOW); cp_method(s, 1, ES_GLOW);
		CHECK(is(s, 255, 1, 2, 3), "none/shadow/glow change nothing yet");
	}
	/* --- scaling */
	{
		uint8_t *a = solid(7, 5, 200, 10, 20, 30), *o = malloc(7 * 5 * 4);
		CHECK(cp_scale(o, 7, 5, a, 7, 5, &mem) == 0 && !memcmp(o, a, 7 * 5 * 4), "identity scale");
		free(o);
		o = malloc(13 * 11 * 4);
		CHECK(cp_scale(o, 13, 11, a, 7, 5, &mem) == 0, "upscale");
		int same = 1;
		for (int i = 0; i < 13 * 11; i++) same &= is(o + i * 4, 200, 10, 20, 30);
		CHECK(same, "upscaled solid stays solid");
		free(o);
		o = malloc(3 * 2 * 4);
		CHECK(cp_scale(o, 3, 2, a, 7, 5, &mem) == 0, "downscale");
		same = 1;
		for (int i = 0; i < 3 * 2; i++) same &= is(o + i * 4, 200, 10, 20, 30);
		CHECK(same, "downscaled solid stays solid");
		free(o); free(a);

		/* 2x1 -> 1x1: opaque red + transparent = half transparent RED (premultiplied, no dark fringe) */
		uint8_t two[8] = { 255, 255, 0, 0, 0, 0, 0, 0 }, one[4];
		CHECK(cp_scale(one, 1, 1, two, 2, 1, &mem) == 0 && one[0] == 128 && one[1] == 255 && one[2] == 0, "premultiplied average %d %d", one[0], one[1]);
		/* 2x1 -> 4x1 bilinear: ends keep their colour, the middle mixes */
		uint8_t bw[8] = { 255, 0, 0, 0, 255, 255, 255, 255 }, four[16];
		CHECK(cp_scale(four, 4, 1, bw, 2, 1, &mem) == 0, "bilinear");
		CHECK(four[1] == 0 && four[13] == 255 && four[5] > 0 && four[5] < 128 && four[9] > 128 && four[9] < 255,
		      "bilinear ramp %d %d %d %d", four[1], four[5], four[9], four[13]);
		failafter = 0;
		CHECK(cp_scale(four, 4, 1, bw, 2, 1, &mem) == -1, "scale: no memory");
		failafter = -1;
	}
	/* --- source over */
	{
		uint8_t *d = solid(4, 4, 255, 0, 0, 255), *s = solid(2, 2, 255, 255, 0, 0);
		cp_over(d, 4, 4, s, 2, 2, 1, 1);
		CHECK(is(px(d, 4, 1, 1), 255, 255, 0, 0) && is(px(d, 4, 0, 0), 255, 0, 0, 255) && is(px(d, 4, 3, 3), 255, 0, 0, 255), "opaque over");
		cp_over(d, 4, 4, s, 2, 2, -1, -1);     /* clipped at the top left */
		CHECK(is(px(d, 4, 0, 0), 255, 255, 0, 0), "clipped over");
		cp_over(d, 4, 4, s, 2, 2, 3, 3);       /* clipped at the bottom right */
		CHECK(is(px(d, 4, 3, 3), 255, 255, 0, 0), "clipped over 2");
		cp_over(d, 4, 4, s, 2, 2, 10, 10);     /* fully outside */
		free(s);
		s = solid(1, 1, 128, 255, 255, 255);
		cp_over(d, 4, 4, s, 1, 1, 2, 0);       /* half white over blue */
		CHECK(px(d, 4, 2, 0)[0] == 255 && px(d, 4, 2, 0)[1] == 128 && px(d, 4, 2, 0)[3] == 255, "half over opaque");
		free(d);
		d = solid(1, 1, 0, 0, 0, 0);
		cp_over(d, 1, 1, s, 1, 1, 0, 0);       /* over transparent: the source itself */
		CHECK(is(d, 128, 255, 255, 255), "over transparent");
		free(d); free(s);
	}
	/* --- emblem size rule */
	{
		ESEmblem e;
		uint32_t w, h;
		memset(&e, 0, sizeof(e));
		cp_emblem_size(&e, 30, 20, &w, &h);  CHECK(w == 30 && h == 20, "own size");
		e.width = 15; cp_emblem_size(&e, 30, 20, &w, &h); CHECK(w == 15 && h == 10, "aspect from width");
		e.width = 0; e.height = 40; cp_emblem_size(&e, 30, 20, &w, &h); CHECK(w == 60 && h == 40, "aspect from height");
		e.width = 7; cp_emblem_size(&e, 30, 20, &w, &h); CHECK(w == 7 && h == 40, "both given");
		e.width = 1; e.height = 0; cp_emblem_size(&e, 3, 100, &w, &h); CHECK(w == 1 && h == 33, "rounding");
		e.width = 0; e.height = 1; cp_emblem_size(&e, 3, 100, &w, &h); CHECK(w == 1 && h == 1, "at least 1");
	}
	/* --- cp_compose */
	{
		CPResult r;
		own[0] = (CPImage){ solid(40, 30, 255, 0, 0, 200), 40, 30 };
		own[1] = (CPImage){ solid(40, 30, 255, 0, 200, 0), 40, 30 };
		named[0] = (CPImage){ solid(64, 64, 255, 100, 100, 100), 64, 64 };
		named[1] = (CPImage){ solid(80, 60, 255, 200, 200, 200), 80, 60 };
		named[2] = (CPImage){ solid(8, 8, 255, 255, 0, 0), 8, 8 };
		named[3] = (CPImage){ solid(300, 10, 255, 1, 1, 1), 300, 10 };

		const char *const none[] = { "DONOTWAIT", NULL };
		CHECK(compose(none, &r) == 0, "no directives");
		const char *const miss[] = { "IMAGE=Nope", "EMBLEM=Nope2", NULL };
		CHECK(compose(miss, &r) == 0, "missing images");
		const char *const huge[] = { "IMAGE=Huge", NULL };
		CHECK(compose(huge, &r) == 0, "too large default image");

		const char *const emb[] = { "EMBLEM=Emb,0,0,5,6", NULL };
		CHECK(compose(emb, &r) == 1 && r.w == 40 && r.h == 30, "emblem on own image");
		CHECK(is(px(r.img[0], 40, 5, 6), 255, 255, 0, 0) && is(px(r.img[0], 40, 12, 13), 255, 255, 0, 0)
		      && is(px(r.img[0], 40, 4, 6), 255, 0, 0, 200) && is(px(r.img[0], 40, 13, 13), 255, 0, 0, 200), "emblem placed");
		CHECK(r.img[1] && is(px(r.img[1], 40, 5, 6), 255, 0, 200, 0), "no EMBLEMSELECTED: selected image unchanged");
		freeres(&r);

		const char *const scaled[] = { "EMBLEM=Emb,16,4,-8,28,DARK", "EMBLEMSELECTED=Emb,2,2,38,0", NULL };
		CHECK(compose(scaled, &r) == 1, "scaled emblem");
		CHECK(is(px(r.img[0], 40, 0, 28), 255, 191, 0, 0) && is(px(r.img[0], 40, 7, 29), 255, 191, 0, 0)
		      && is(px(r.img[0], 40, 8, 28), 255, 0, 0, 200) && is(px(r.img[0], 40, 0, 27), 255, 0, 0, 200), "scaled, dark, clipped");
		CHECK(is(px(r.img[1], 40, 38, 0), 255, 255, 0, 0) && is(px(r.img[1], 40, 39, 1), 255, 255, 0, 0)
		      && is(px(r.img[1], 40, 37, 0), 255, 0, 200, 0), "selected emblem");
		freeres(&r);

		const char *const img[] = { "IMAGE=Base,BRIGHT", "IMAGESELECTED=Sel,GRAY", NULL };
		CHECK(compose(img, &r) == 1 && r.w == 64 && r.h == 64, "default images");
		CHECK(is(px(r.img[0], 64, 0, 0), 255, 139, 139, 139), "bright base %d", px(r.img[0], 64, 0, 0)[1]);
		CHECK(is(px(r.img[1], 64, 0, 2), 255, 200, 200, 200) && is(px(r.img[1], 64, 0, 1), 0, 0, 0, 0)
		      && is(px(r.img[1], 64, 63, 61), 255, 200, 200, 200) && is(px(r.img[1], 64, 63, 62), 0, 0, 0, 0),
		      "selected 80x60 centred on 64x64: clipped sideways, 2 empty rows top and bottom; gray");
		freeres(&r);

		/* INTERNAL: the icon's own images as the emblem, only together with IMAGE */
		const char *const in1[] = { "EMBLEM=INTERNAL,20,15,2,2", NULL };
		CHECK(compose(in1, &r) == 0, "INTERNAL without IMAGE ignored");
		const char *const in2[] = { "IMAGE=Base", "IMAGESELECTED=Base", "EMBLEM=INTERNAL,20,15,2,2", "EMBLEMSELECTED=INTERNAL,0,0,10,10", NULL };
		CHECK(compose(in2, &r) == 1, "INTERNAL with IMAGE");
		CHECK(is(px(r.img[0], 64, 2, 2), 255, 0, 0, 200) && is(px(r.img[0], 64, 21, 16), 255, 0, 0, 200)
		      && is(px(r.img[0], 64, 22, 2), 255, 100, 100, 100), "own normal image as emblem, scaled to 20x15");
		CHECK(is(px(r.img[1], 64, 10, 10), 255, 0, 200, 0) && is(px(r.img[1], 64, 49, 39), 255, 0, 200, 0)
		      && is(px(r.img[1], 64, 50, 40), 255, 100, 100, 100), "own selected image as selected emblem, own size");
		freeres(&r);

		/* no selected image anywhere: EMBLEMSELECTED is ignored, no selected image made */
		free((void *)own[1].px);
		own[1].px = NULL;
		const char *const nosel[] = { "EMBLEMSELECTED=Emb", NULL };
		CHECK(compose(nosel, &r) == 0, "EMBLEMSELECTED without a selected image");
		const char *const nosel2[] = { "EMBLEM=Emb", "EMBLEMSELECTED=Emb", NULL };
		CHECK(compose(nosel2, &r) == 1 && r.img[1] == NULL, "only the normal image");
		freeres(&r);

		const char *const big[] = { "EMBLEM=Emb,600,10", NULL };
		CHECK(compose(big, &r) == 0, "emblem larger than 512 ignored");
		const char *const off[] = { "EMBLEM=Emb,0,0,500,500", NULL };
		CHECK(compose(off, &r) == 1 && !memcmp(r.img[0], own[0].px, 40 * 30 * 4), "emblem off the image: unchanged copy");
		freeres(&r);

		/* memory running out at every allocation: -1, nothing leaks (ASan) */
		const char *const all[] = { "IMAGE=Base", "IMAGESELECTED=Sel", "EMBLEM=Emb,20,20,1,1", "EMBLEMSELECTED=Emb,3,3", NULL };
		own[1] = (CPImage){ solid(40, 30, 255, 0, 200, 0), 40, 30 };
		int ok = 1, k;
		for (k = 0; k < 10; k++)
		{
			failafter = k;
			int rr = compose(all, &r);
			if (rr == 1) { freeres(&r); break; }
			ok &= rr == -1;
		}
		failafter = -1;
		CHECK(ok && k > 3, "out of memory paths (%d)", k);

		/* --- SHADOW and GLOW on a transparent 40x30 icon */
		{
			uint8_t *keep0 = (uint8_t *)own[0].px, *keep1 = (uint8_t *)own[1].px;
			own[0] = (CPImage){ solid(40, 30, 0, 0, 0, 0), 40, 30 };
			own[1].px = NULL;
			named[5] = (CPImage){ solid(16, 16, 255, 255, 0, 0), 16, 16 };
			const char *const sh[] = { "EMBLEM=Big,0,0,4,4,SHADOW", NULL };
			CHECK(compose(sh, &r) == 1, "shadow");
			CHECK(is(px(r.img[0], 40, 10, 10), 255, 255, 0, 0), "emblem on top of its shadow");
			const uint8_t *q = px(r.img[0], 40, 22, 12);   /* right of the emblem (4..19), inside the shadow (9..24) */
			CHECK(q[0] > 0 && q[0] <= 128 && q[1] == 0 && q[2] == 0 && q[3] == 0, "soft black shadow %d", q[0]);
			q = px(r.img[0], 40, 20, 20);   /* shadow 9..24, fully dark from 13 to 20; emblem ends at 19 */
			CHECK(q[0] == 128 && q[1] == 0, "full shadow inside: 50 %% (%d)", q[0]);
			CHECK(px(r.img[0], 40, 3, 12)[0] == 0 && px(r.img[0], 40, 12, 3)[0] == 0, "no shadow left/above (offset +5,+5)");
			CHECK(px(r.img[0], 40, 35, 12)[0] == 0, "shadow ends");
			freeres(&r);

			const char *const gl[] = { "EMBLEM=Big,0,0,12,8,GLOW", NULL };
			CHECK(compose(gl, &r) == 1, "glow");
			q = px(r.img[0], 40, 10, 16);    /* 2 left of the emblem (12..27) */
			CHECK(q[0] > 0 && q[1] == 255 && q[2] == 255 && q[3] == 255, "white glow outside %d", q[0]);
			CHECK(px(r.img[0], 40, 2, 16)[0] == 0, "glow fades out");
			CHECK(is(px(r.img[0], 40, 20, 16), 255, 255, 0, 0), "emblem on top of its glow");
			freeres(&r);

			/* clipping: an emblem in the corner, its shadow partly outside; one fully outside whose shadow reaches in */
			const char *const cl[] = { "EMBLEM=Big,0,0,30,20,SHADOW", NULL };
			CHECK(compose(cl, &r) == 1 && px(r.img[0], 40, 39, 29)[0] > 0, "clipped shadow");
			freeres(&r);
			const char *const cl2[] = { "EMBLEM=Big,0,0,-19,-19,SHADOW", NULL };
			CHECK(compose(cl2, &r) == 1 && px(r.img[0], 40, 0, 0)[0] > 0 && px(r.img[0], 40, 0, 0)[1] == 0,
			      "emblem outside, its shadow reaches in (%d)", px(r.img[0], 40, 0, 0)[0]);
			freeres(&r);

			/* SHADOW on a default image: under the image, inside the image's rectangle */
			uint8_t *mg = solid(64, 64, 0, 0, 0, 0);
			for (int y = 10; y < 50; y++) for (int x = 10; x < 50; x++) { uint8_t *p = mg + (y * 64 + x) * 4; p[0] = 255; p[1] = 200; }
			named[4] = (CPImage){ mg, 64, 64 };
			const char *const ims[] = { "IMAGE=Margin,SHADOW", NULL };
			CHECK(compose(ims, &r) == 1, "image shadow");
			CHECK(is(px(r.img[0], 64, 30, 30), 255, 200, 0, 0) && px(r.img[0], 64, 53, 53)[0] > 0
			      && px(r.img[0], 64, 53, 53)[1] == 0 && px(r.img[0], 64, 5, 5)[0] == 0, "shadow under the default image");
			freeres(&r);

			/* prefs: the methods for tool types without one, and the settings */
			parse_prefs("EMBLEMMETHOD=GLOW\nIMAGEMETHOD=GRAY\nGLOWCOLOR=00FF00");
			const char *const pd[] = { "IMAGE=Margin", "EMBLEM=Big,0,0,12,8", NULL };
			CHECK(compose(pd, &r) == 1, "prefs methods");
			CHECK(is(px(r.img[0], 64, 20, 16), 255, 255, 0, 0), "emblem (12..27 x 8..23) as it is");
			CHECK(is(px(r.img[0], 64, 30, 30), 255, 60, 60, 60), "IMAGEMETHOD=GRAY on the image");
			q = px(r.img[0], 64, 9, 60);
			CHECK(q[0] == 0, "nothing far away");
			q = px(r.img[0], 64, 8, 16);   /* left of the image (10..49) and the emblem: green glow on transparent */
			CHECK(q[0] > 0 && q[1] == 0 && q[2] == 255 && q[3] == 0, "green glow from GLOWCOLOR (%d %d %d %d)", q[0], q[1], q[2], q[3]);
			freeres(&r);
			parse_prefs("METHOD=SHADOW\nSHADOWOPACITY=0");
			const char *const nop[] = { "EMBLEM=Big,0,0,4,4", NULL };
			CHECK(compose(nop, &r) == 1 && px(r.img[0], 40, 22, 12)[0] == 0, "opacity 0: no shadow");
			freeres(&r);
			parse_prefs("METHOD=SHADOW\nSHADOWBLUR=0\nSHADOWOFFSET=-3,2\nSHADOWOPACITY=100");
			CHECK(compose(nop, &r) == 1 && is(px(r.img[0], 40, 1, 21), 255, 0, 0, 0) && px(r.img[0], 40, 0, 21)[0] == 0,
			      "hard shadow at -3,+2");
			freeres(&r);
			ep_defaults(&prefs);
			free((void *)own[0].px);
			own[0].px = keep0;
			own[1].px = keep1;
		}

		/* the scaled-emblem cache changes nothing: same pixels, a hit the second time */
		{
			const char *const sct[] = { "EMBLEM=Emb,20,20,3,3,SHADOW", "EMBLEMSELECTED=Emb,5,0,1,1,GLOW", NULL };
			CPResult a, b, c2;
			usecache = 0;
			int ra = compose(sct, &a);
			usecache = 1;
			int rb = compose(sct, &b);
			int h0 = hits;
			int rc = compose(sct, &c2);
			CHECK(ra == 1 && rb == 1 && rc == 1 && stores == 2 && hits - h0 == 2, "cache used (%d stores, %d hits)", stores, hits - h0);
			CHECK(!memcmp(a.img[0], b.img[0], 40 * 30 * 4) && !memcmp(a.img[0], c2.img[0], 40 * 30 * 4)
			      && !memcmp(a.img[1], c2.img[1], 40 * 30 * 4), "same pixels with and without the cache");
			freeres(&a); freeres(&b); freeres(&c2);
			usecache = 0;
			for (int i = 0; i < nsc; i++) free(sc[i].px);
			nsc = 0;
		}

		/* random tool types: no crash, results inside bounds (ASan) */
		unsigned seed = 1;
		for (int t = 0; t < 2000; t++)
		{
			char a[80], b[80];
			seed = seed * 1103515245u + 12345u;
			snprintf(a, sizeof(a), "EMBLEM=%s,%d,%d,%d,%d", (seed >> 4) & 1 ? "Emb" : "Base",
			         (int)((seed >> 8) % 90), (int)((seed >> 12) % 90), (int)((seed >> 16) % 140) - 70, (int)((seed >> 20) % 140) - 70);
			snprintf(b, sizeof(b), "IMAGE=%s", (seed >> 5) & 1 ? "Base" : "None");
			static const char *const meth[] = { "NONE", "SHADOW", "GLOW", "GRAY", "DARK" };
			char c[80];
			snprintf(c, sizeof(c), "EMBLEMSELECTED=Emb,%d,0,%d,%d,%s", (int)((seed >> 3) % 40), (int)((seed >> 9) % 80) - 40,
			         (int)((seed >> 13) % 80) - 40, meth[(seed >> 24) % 5]);
			strcat(a, (seed >> 26) & 1 ? ",SHADOW" : ",GLOW");
			const char *const tt[] = { a, b, c, NULL };
			if (compose(tt, &r) == 1) freeres(&r);
		}
		for (int i = 0; i < 6; i++) free((void *)named[i].px);
		free((void *)own[0].px);
		free((void *)own[1].px);
	}

	printf("%s: %d failure(s)\n", fails ? "FAILED" : "OK", fails);
	return fails ? 1 : 0;
}
