/*
 * emblemprefs.c - parse the global settings file (see emblemprefs.h).
 */
#include "emblemprefs.h"

void ep_defaults(CPPrefs *p)
{
	p->imagemethod   = ES_NONE;
	p->emblemmethod  = ES_NONE;
	p->shadowx       = 5;
	p->shadowy       = 5;
	p->shadowblur    = 2;
	p->shadowopacity = 50;
	p->glowsize      = 2;
	p->glowopacity   = 80;
	p->glowrgb[0] = p->glowrgb[1] = p->glowrgb[2] = 255;
}

static int up(int c) { return (c >= 'a' && c <= 'z') ? c - 32 : c; }
static int space(int c) { return c == ' ' || c == '\t'; }

static int eqi(const char *s, uint32_t len, const char *word)
{
	uint32_t i;
	for (i = 0; i < len && word[i]; i++)
		if (up((uint8_t)s[i]) != up((uint8_t)word[i])) return 0;
	return i == len && word[i] == 0;
}

/* integer in [lo, hi]; 1 = ok */
static int number(const char *s, uint32_t len, int32_t lo, int32_t hi, int32_t *out)
{
	uint32_t i = 0;
	int neg = 0;
	int32_t v = 0;
	if (len && (s[0] == '-' || s[0] == '+')) { neg = s[0] == '-'; i++; }
	if (i == len) return 0;
	for (; i < len; i++)
	{
		if (s[i] < '0' || s[i] > '9' || v > 10000) return 0;
		v = v * 10 + (s[i] - '0');
	}
	if (neg) v = -v;
	if (v < lo || v > hi) return 0;
	*out = v;
	return 1;
}

static int hexcolour(const char *s, uint32_t len, uint8_t *rgb)
{
	uint32_t i, v = 0;
	if (len && (s[0] == '#' || s[0] == '$')) { s++; len--; }
	else if (len > 2 && s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) { s += 2; len -= 2; }
	if (len != 6) return 0;
	for (i = 0; i < 6; i++)
	{
		int c = up((uint8_t)s[i]), d;
		if (c >= '0' && c <= '9') d = c - '0';
		else if (c >= 'A' && c <= 'F') d = c - 'A' + 10;
		else return 0;
		v = v * 16 + (uint32_t)d;
	}
	rgb[0] = (uint8_t)(v >> 16);
	rgb[1] = (uint8_t)(v >> 8);
	rgb[2] = (uint8_t)v;
	return 1;
}

int ep_parse(const char *text, uint32_t len, CPPrefs *p)
{
	uint32_t pos = 0;
	int n = 0, both = -1, img = -1, emb = -1;

	while (pos < len)
	{
		const char *line = text + pos, *key, *val;
		uint32_t ll = 0, kl, vl, eq;
		int32_t a, b;
		int m;

		while (pos + ll < len && line[ll] != '\n' && line[ll] != '\r' && line[ll] != 0) ll++;
		pos += ll + 1;
		while (ll && space((uint8_t)line[0])) { line++; ll--; }
		while (ll && space((uint8_t)line[ll - 1])) ll--;
		if (!ll || line[0] == '#' || line[0] == ';') continue;
		for (eq = 0; eq < ll && line[eq] != '='; eq++) ;
		if (eq == ll) continue;
		key = line;
		kl = eq;
		while (kl && space((uint8_t)key[kl - 1])) kl--;
		val = line + eq + 1;
		vl = ll - eq - 1;
		while (vl && space((uint8_t)val[0])) { val++; vl--; }

		if (eqi(key, kl, "METHOD") || eqi(key, kl, "IMAGEMETHOD") || eqi(key, kl, "EMBLEMMETHOD"))
		{
			if ((m = es_method(val, vl)) <= ES_DEFAULT) continue;
			if (eqi(key, kl, "METHOD")) both = m;
			else if (eqi(key, kl, "IMAGEMETHOD")) img = m;
			else emb = m;
			n++;
		}
		else if (eqi(key, kl, "SHADOWOFFSET"))
		{
			uint32_t c;
			for (c = 0; c < vl && val[c] != ','; c++) ;
			if (c == vl)
			{
				if (!number(val, vl, -16, 16, &a)) continue;
				b = a;
			}
			else
			{
				uint32_t s2 = c + 1, e1 = c;
				while (e1 && space((uint8_t)val[e1 - 1])) e1--;
				while (s2 < vl && space((uint8_t)val[s2])) s2++;
				if (!number(val, e1, -16, 16, &a) || !number(val + s2, vl - s2, -16, 16, &b)) continue;
			}
			p->shadowx = (int8_t)a;
			p->shadowy = (int8_t)b;
			n++;
		}
		else if (eqi(key, kl, "SHADOWBLUR") && number(val, vl, 0, 8, &a))      { p->shadowblur = (uint8_t)a; n++; }
		else if (eqi(key, kl, "SHADOWOPACITY") && number(val, vl, 0, 100, &a)) { p->shadowopacity = (uint8_t)a; n++; }
		else if (eqi(key, kl, "GLOWSIZE") && number(val, vl, 1, 8, &a))        { p->glowsize = (uint8_t)a; n++; }
		else if (eqi(key, kl, "GLOWOPACITY") && number(val, vl, 0, 100, &a))   { p->glowopacity = (uint8_t)a; n++; }
		else if (eqi(key, kl, "GLOWCOLOR") || eqi(key, kl, "GLOWCOLOUR"))
		{
			if (hexcolour(val, vl, p->glowrgb)) n++;
		}
	}
	/* METHOD sets both, the specific keys win wherever they are in the file */
	if (both >= 0) { p->imagemethod = (uint8_t)both; p->emblemmethod = (uint8_t)both; }
	if (img >= 0) p->imagemethod = (uint8_t)img;
	if (emb >= 0) p->emblemmethod = (uint8_t)emb;
	return n;
}
