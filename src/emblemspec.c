/*
 * emblemspec.c - parse the Emblem settings (see emblemspec.h).
 */
#include "emblemspec.h"

static const char *const methods[ES_NMETHODS] = { "", "NONE", "SHADOW", "GLOW", "GRAY", "DARK", "BRIGHT" };

static int up(int c) { return (c >= 'a' && c <= 'z') ? c - 32 : c; }
static int space(int c) { return c == ' ' || c == '\t'; }

static int eqi(const char *s, uint32_t len, const char *word)
{
	uint32_t i;
	for (i = 0; i < len && word[i]; i++)
		if (up((uint8_t)s[i]) != up((uint8_t)word[i])) return 0;
	return i == len && word[i] == 0;
}

int es_method(const char *s, uint32_t len)
{
	int m;
	if (len == 0) return ES_DEFAULT;
	for (m = 1; m < ES_NMETHODS; m++)
		if (eqi(s, len, methods[m])) return m;
	if (eqi(s, len, "GREY")) return ES_GRAY;
	return -1;
}

int es_valid_name(const char *s, uint32_t len)
{
	uint32_t i;
	if (len == 0 || len >= ES_NAMELEN || s[0] == '/') return 0;
	for (i = 0; i < len; i++)
		if ((uint8_t)s[i] < 32 || s[i] == ':' || s[i] == 127) return 0;
	return 1;
}

/* Split value into comma-separated fields, trimmed. Returns the field count (max n). */
static int fields(const char *v, uint32_t len, const char **f, uint32_t *fl, int n)
{
	int k = 0;
	uint32_t i = 0;
	while (k < n)
	{
		uint32_t start = i, end;
		while (i < len && v[i] != ',') i++;
		end = i;
		while (start < end && space((uint8_t)v[start])) start++;
		while (end > start && space((uint8_t)v[end - 1])) end--;
		f[k] = v + start;
		fl[k] = end - start;
		k++;
		if (i >= len) break;
		i++;   /* skip the comma */
	}
	if (i < len) return -1;   /* too many fields */
	return k;
}

static int number(const char *s, uint32_t len, int32_t *out)
{
	uint32_t i = 0;
	int neg = 0;
	int32_t v = 0;
	if (len == 0) { *out = 0; return 1; }
	if (s[0] == '-' || s[0] == '+') { neg = s[0] == '-'; i++; }
	if (i == len) return 0;
	for (; i < len; i++)
	{
		if (s[i] < '0' || s[i] > '9' || v > 100000) return 0;
		v = v * 10 + (s[i] - '0');
	}
	*out = neg ? -v : v;
	return 1;
}

static void copyname(char *d, const char *s, uint32_t len)
{
	uint32_t i;
	for (i = 0; i < len; i++) d[i] = s[i];
	d[len] = 0;
}

static int parse_image(const char *v, uint32_t len, ESImage *img)
{
	const char *f[2];
	uint32_t fl[2];
	int n = fields(v, len, f, fl, 2), m = ES_DEFAULT;
	if (n < 1 || !es_valid_name(f[0], fl[0])) return 0;
	if (n > 1 && (m = es_method(f[1], fl[1])) < 0) return 0;
	img->set = 1;
	img->method = (uint8_t)m;
	copyname(img->name, f[0], fl[0]);
	return 1;
}

static int parse_emblem(const char *v, uint32_t len, ESEmblem *em)
{
	const char *f[6];
	uint32_t fl[6];
	int32_t num[4] = { 0, 0, 0, 0 };
	int n = fields(v, len, f, fl, 6), m = ES_DEFAULT, i;
	if (n < 1 || !es_valid_name(f[0], fl[0])) return 0;
	for (i = 1; i < n && i < 5; i++)
		if (!number(f[i], fl[i], &num[i - 1])) return 0;
	if (n > 5 && (m = es_method(f[5], fl[5])) < 0) return 0;
	em->set = 1;
	em->method = (uint8_t)m;
	em->internal = eqi(f[0], fl[0], "INTERNAL") ? 1 : 0;
	copyname(em->name, f[0], fl[0]);
	em->width  = num[0] > 0 ? num[0] : 0;
	em->height = num[1] > 0 ? num[1] : 0;
	em->x = num[2];
	em->y = num[3];
	return 1;
}

int es_parse(const char *tt, uint32_t len, ESpec *spec)
{
	static const char *const keys[4] = { "IMAGE", "IMAGESELECTED", "EMBLEM", "EMBLEMSELECTED" };
	uint32_t pos = 0, i;
	uint8_t seen[4] = { 0, 0, 0, 0 };
	int found = 0, k;
	uint8_t *p = (uint8_t *)spec;

	for (i = 0; i < sizeof(*spec); i++) p[i] = 0;
	if (!tt) return 0;
	while (pos < len)
	{
		const char *s = tt + pos;
		uint32_t slen = 0, eq;
		while (pos + slen < len && s[slen]) slen++;
		pos += slen + 1;
		for (eq = 0; eq < slen && s[eq] != '='; eq++) ;
		if (eq == slen) continue;
		for (k = 0; k < 4; k++)
		{
			if (seen[k] || !eqi(s, eq, keys[k])) continue;
			seen[k] = 1;   /* the first one counts, even if it is malformed */
			if (k < 2 ? parse_image(s + eq + 1, slen - eq - 1, &spec->image[k])
			          : parse_emblem(s + eq + 1, slen - eq - 1, &spec->emblem[k - 2]))
				found++;
			break;
		}
	}
	return found;
}
