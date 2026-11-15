/*
 * compose.h - ARGB image helpers for the icon module, portable C.
 * Pixels are 4 bytes A, R, G, B (big-endian 0xAARRGGBB, icon.library's
 * direct mapped format).
 */
#ifndef EMBLEM_COMPOSE_H
#define EMBLEM_COMPOSE_H

#include <stdint.h>

/* Palette mapped pixels -> ARGB. transparent = -1 for none; indices beyond
 * the palette become opaque black. */
void cp_from_clut(uint8_t *dst, const uint8_t *px, uint32_t n,
                  const uint8_t *palette, uint32_t palsize, int32_t transparent);

/* Planar image (depth planes of height rows of ((width+15)/16) big-endian
 * words) -> ARGB, with Workbench's default pens: 0 transparent, 1 black,
 * 2 white, 3 blue, 4-7 the MagicWB greys and colours, higher pens grey. */
void cp_from_planar(uint8_t *dst, uint32_t width, uint32_t height,
                    const uint8_t *planes, uint32_t depth);

/* Copy src (sw x sh) centred into dst (dw x dh), clipped; the rest of dst
 * becomes transparent. */
void cp_place_centred(uint8_t *dst, uint32_t dw, uint32_t dh,
                      const uint8_t *src, uint32_t sw, uint32_t sh);

/* ---- composition (integer only: the same pixels on every CPU) ---- */

#include "emblemspec.h"

#define CP_MAXCANVAS 256    /* largest icon image */
#define CP_MAXSOURCE 1024   /* largest emblem source image */
#define CP_MAXEMBLEM 512    /* largest emblem after scaling */

typedef struct CPImage
{
	const uint8_t *px;      /* ARGB */
	uint32_t       w, h;
} CPImage;

typedef struct CPMem
{
	void *(*alloc)(void *ctx, uint32_t size);
	void  (*free)(void *ctx, void *p);      /* may be NULL for the output allocator */
	void  *ctx;
} CPMem;

/* Image source for cp_compose(): name != NULL asks for a default image or
 * emblem by name; name == NULL for the icon's own image `own` (0 normal,
 * 1 selected). Return 1 and fill img if there is one. */
typedef int (*cp_image_fn)(void *ctx, const char *name, int own, CPImage *img);

typedef struct CPResult
{
	uint8_t *img[2];        /* normal, selected (NULL: none) */
	uint32_t w, h;
} CPResult;

/* Global settings (emblem.prefs, see src/emblemprefs.h) */
typedef struct CPPrefs
{
	uint8_t imagemethod;    /* for IMAGE=/IMAGESELECTED= without a method */
	uint8_t emblemmethod;   /* for EMBLEM=/EMBLEMSELECTED= without a method */
	int8_t  shadowx, shadowy;   /* SHADOW: offset (spec: +5,+5) */
	uint8_t shadowblur;     /* blur radius, 0 = hard */
	uint8_t shadowopacity;  /* percent */
	uint8_t glowsize;       /* GLOW: how far it reaches out, 1.. */
	uint8_t glowopacity;    /* percent */
	uint8_t glowrgb[3];
} CPPrefs;

/* Apply a colour method (ES_DARK, ES_BRIGHT, ES_GRAY; others change nothing)
 * to n straight-alpha ARGB pixels. */
void cp_method(uint8_t *px, uint32_t n, int method);

/* Draw the SHADOW or GLOW layer of src (sw x sh, placed at x, y) onto dst,
 * clipped; draw src itself over it afterwards. 0 = ok, -1 = no memory. */
int cp_effect(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
              int32_t x, int32_t y, int method, const CPPrefs *prefs, const CPMem *tmp);

/* Scale src (sw x sh) to dst (dw x dh): area average when shrinking, bilinear
 * when growing, per axis, in premultiplied alpha. 0 = ok, -1 = no memory. */
int cp_scale(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
             const CPMem *tmp);

/* Draw src (sw x sh) over dst (dw x dh) with its top left corner at x, y
 * ("source over"), clipped to dst. */
void cp_over(uint8_t *dst, uint32_t dw, uint32_t dh, const uint8_t *src, uint32_t sw, uint32_t sh,
             int32_t x, int32_t y);

/* Emblem size from the tool type: 0,0 = the emblem's own size; one of them 0
 * = keep the aspect ratio. */
void cp_emblem_size(const ESEmblem *e, uint32_t sw, uint32_t sh, uint32_t *w, uint32_t *h);

/* Optional cache of scaled emblems (by name and size), so the same emblem at
 * the same size is scaled once: find returns the pixels or NULL, store keeps
 * a copy. Results are the same with or without it. */
typedef struct CPScaleCache
{
	const uint8_t *(*find)(void *ctx, const char *name, uint32_t w, uint32_t h);
	void           (*store)(void *ctx, const char *name, uint32_t w, uint32_t h, const uint8_t *px);
	void            *ctx;
} CPScaleCache;

/* Compose an icon's images from its tool types (docs/plan.md section 1).
 * prefs supplies the methods for ES_DEFAULT and the effect settings; cache
 * may be NULL. Returns 1 with res filled (buffers from out), 0 if there is
 * nothing to compose, -1 if memory ran out. */
int cp_compose(const ESpec *spec, const CPPrefs *prefs, cp_image_fn get, void *gctx,
               const CPMem *out, const CPMem *tmp, const CPScaleCache *cache, CPResult *res);

#endif
