/* Host tests for src/emblemspec.c (tool type parsing) and src/compose.c (ARGB helpers). */
#include "../../src/emblemspec.h"
#include "../../src/compose.h"
#include <stdio.h>
#include <string.h>

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

/* pack "a\0b\0" from a list */
static uint32_t pack(char *buf, const char *const *tt)
{
	uint32_t n = 0;
	for (; *tt; tt++) { strcpy(buf + n, *tt); n += (uint32_t)strlen(*tt) + 1; }
	return n;
}

static int parse(ESpec *s, const char *const *tt)
{
	char buf[2048];
	return es_parse(buf, pack(buf, tt), s);
}

int main(void)
{
	ESpec s;

	{   /* the spec's examples */
		const char *const tt[] = { "IMAGE=DrawerNS", "IMAGESELECTED=DrawerS",
			"EMBLEM=EmblemDevs,12,12,10,5,SHADOW", "EMBLEMSELECTED=EmblemDevs,12,12,9,6,SHADOW", NULL };
		CHECK(parse(&s, tt) == 4, "devs: 4 directives");
		CHECK(s.image[0].set && !strcmp(s.image[0].name, "DrawerNS") && s.image[0].method == ES_DEFAULT, "IMAGE");
		CHECK(s.image[1].set && !strcmp(s.image[1].name, "DrawerS"), "IMAGESELECTED");
		CHECK(s.emblem[0].set && !strcmp(s.emblem[0].name, "EmblemDevs") && s.emblem[0].width == 12
		      && s.emblem[0].height == 12 && s.emblem[0].x == 10 && s.emblem[0].y == 5
		      && s.emblem[0].method == ES_SHADOW && !s.emblem[0].internal, "EMBLEM");
		CHECK(s.emblem[1].x == 9 && s.emblem[1].y == 6, "EMBLEMSELECTED");
	}
	{
		const char *const tt[] = { "EMBLEM=EmblemPrefs,10,10,15,20,NONE", "EMBLEMSELECTED=EmblemPrefs,10,10,15,20,GLOW", NULL };
		CHECK(parse(&s, tt) == 2 && !s.image[0].set && s.emblem[0].method == ES_NONE && s.emblem[1].method == ES_GLOW, "mui");
	}
	{
		const char *const tt[] = { "IMAGE=Drawer", "IMAGESELECTED=Drawer", "EMBLEM=INTERNAL,10,10,15,20",
			"EMBLEMSELECTED=internal,10,10,15,20", NULL };
		CHECK(parse(&s, tt) == 4 && s.emblem[0].internal && s.emblem[1].internal
		      && s.emblem[0].method == ES_DEFAULT, "internal");
	}
	{   /* defaults, spaces, case, methods */
		const char *const tt[] = { "image= DrawerNS , dark", "IMAGE =ignored", "Emblem=E1", "EMBLEMSELECTED=E2,,,3", NULL };
		CHECK(parse(&s, tt) == 3, "loose syntax count");
		CHECK(!strcmp(s.image[0].name, "DrawerNS") && s.image[0].method == ES_DARK, "trimmed + method");
		CHECK(s.emblem[0].set && s.emblem[0].width == 0 && s.emblem[0].x == 0 && s.emblem[0].method == ES_DEFAULT, "emblem defaults");
		CHECK(s.emblem[1].x == 3 && s.emblem[1].y == 0, "empty fields");
	}
	{   /* bad ones are ignored; the first key counts */
		const char *const tt[] = { "IMAGE=Bad:Name", "IMAGE=Second", "IMAGESELECTED=X,WOBBLE",
			"EMBLEM=E,1,2,x,4", "EMBLEMSELECTED=E,1,2,3,4,NONE,extra", "(IMAGE=Off)", "IMAGEX=1", "DONOTWAIT", NULL };
		CHECK(parse(&s, tt) == 0, "all bad: %d", parse(&s, tt));
	}
	{
		const char *const tt[] = { "EMBLEM=/up", "IMAGE=", "IMAGESELECTED=Sub/Dir.png", "EMBLEMSELECTED=E,-5,-7,-3,-4", NULL };
		CHECK(parse(&s, tt) == 2 && !s.emblem[0].set && !s.image[0].set, "names");
		CHECK(!strcmp(s.image[1].name, "Sub/Dir.png"), "sub drawer name");
		CHECK(s.emblem[1].width == 0 && s.emblem[1].height == 0 && s.emblem[1].x == -3 && s.emblem[1].y == -4, "negatives");
	}
	{
		char name[100];
		memset(name, 'a', 70); name[70] = 0;
		char tt[120];
		snprintf(tt, sizeof(tt), "IMAGE=%s", name);
		const char *const l[] = { tt, NULL };
		CHECK(parse(&s, l) == 0, "too long name");
	}
	CHECK(es_parse(NULL, 0, &s) == 0, "no tool types");
	CHECK(es_method("grey", 4) == ES_GRAY && es_method("Bright", 6) == ES_BRIGHT && es_method("x", 1) == -1, "methods");

	/* compose helpers */
	{
		uint8_t pal[] = { 10, 20, 30, 40, 50, 60 }, px[] = { 0, 1, 2 }, out[12];
		cp_from_clut(out, px, 3, pal, 2, 0);
		CHECK(out[0] == 0 && out[3] == 0, "clut transparent");
		CHECK(out[4] == 255 && out[5] == 40 && out[6] == 50 && out[7] == 60, "clut colour");
		CHECK(out[8] == 255 && out[9] == 0, "clut out of range");
	}
	{   /* 3x2, depth 2: row 0 = pens 1,2,3; row 1 = 0,0,0 */
		uint8_t planes[2 * 2 * 2] = { 0xA0, 0, 0, 0, 0x60, 0, 0, 0 }, out[3 * 2 * 4];
		cp_from_planar(out, 3, 2, planes, 2);
		CHECK(out[0] == 255 && out[1] == 0, "pen 1 black");
		CHECK(out[4] == 255 && out[5] == 255, "pen 2 white");
		CHECK(out[8] == 255 && out[9] == 0x66 && out[11] == 0xBB, "pen 3 blue");
		CHECK(out[12] == 0, "pen 0 transparent");
	}
	{
		uint8_t src[2 * 2 * 4], dst[4 * 4 * 4], big[6 * 6 * 4];
		memset(src, 0xFF, sizeof(src));
		cp_place_centred(dst, 4, 4, src, 2, 2);
		CHECK(dst[0] == 0 && dst[4 * (1 * 4 + 1)] == 0xFF && dst[4 * (2 * 4 + 2)] == 0xFF && dst[4 * (3 * 4 + 3)] == 0, "centred");
		memset(big, 0x11, sizeof(big));
		big[4 * (1 * 6 + 1)] = 0x77;
		cp_place_centred(dst, 4, 4, big, 6, 6);
		CHECK(dst[0] == 0x77 && dst[4 * 15] == 0x11, "clipped");
	}

	printf("%s: %d failure(s)\n", fails ? "FAILED" : "OK", fails);
	return fails ? 1 : 0;
}
