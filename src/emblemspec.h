/*
 * emblemspec.h - the emblem tool types (docs/plan.md section 1), portable C.
 *
 *   IMAGE=Name[,Method]
 *   IMAGESELECTED=Name[,Method]
 *   EMBLEM=Name[,Width,Height,X,Y,Method]          Name may be INTERNAL
 *   EMBLEMSELECTED=Name[,Width,Height,X,Y,Method]
 *
 * Keys are case-insensitive; the first occurrence of a key counts (like
 * icon.library's FindToolType). Empty fields take their defaults
 * (method: the global preference, numbers: 0). A malformed directive is
 * ignored as a whole.
 */
#ifndef EMBLEMSPEC_H
#define EMBLEMSPEC_H

#include <stdint.h>

#define ES_NAMELEN 64

enum { ES_DEFAULT = 0, ES_NONE, ES_SHADOW, ES_GLOW, ES_GRAY, ES_DARK, ES_BRIGHT, ES_NMETHODS };

typedef struct ESImage
{
	uint8_t set;
	uint8_t method;
	char    name[ES_NAMELEN];
} ESImage;

typedef struct ESEmblem
{
	uint8_t set;
	uint8_t method;
	uint8_t internal;          /* Name was INTERNAL: the icon's own images */
	char    name[ES_NAMELEN];
	int32_t width, height;     /* 0 = the emblem's own size */
	int32_t x, y;
} ESEmblem;

typedef struct ESpec
{
	ESImage  image[2];         /* [0] IMAGE, [1] IMAGESELECTED */
	ESEmblem emblem[2];        /* [0] EMBLEM, [1] EMBLEMSELECTED */
} ESpec;

/* Parse a packed tool type block (NUL-terminated strings one after the other).
 * Returns the number of directives found (0 = nothing to do). */
int es_parse(const char *tt, uint32_t len, ESpec *spec);

/* Method word (case-insensitive, len chars) -> ES_*; -1 if unknown. */
int es_method(const char *s, uint32_t len);

/* Image names: not empty, no ':', not starting with '/', printable, < ES_NAMELEN. */
int es_valid_name(const char *s, uint32_t len);

#endif
