/*
 * png.h - small PNG decoder to 32-bit ARGB, portable C without a C library.
 *
 * All PNG colour types and bit depths, tRNS, Adam7 interlacing. Output is
 * width x height pixels of 4 bytes A, R, G, B (so a big-endian uint32 is
 * 0xAARRGGBB, the icon.library direct mapped format). 16-bit samples keep
 * their high byte. The zlib stream is inflated by the caller's function.
 */
#ifndef EMBLEM_PNG_H
#define EMBLEM_PNG_H

#include <stdint.h>

#define PNG_MAXDIM 1024

enum
{
	PNG_OK = 0,
	PNG_ERR_FORMAT,       /* not a PNG / broken structure */
	PNG_ERR_CRC,          /* chunk CRC mismatch */
	PNG_ERR_UNSUPPORTED,  /* unknown critical chunk, bad header values */
	PNG_ERR_SIZE,         /* larger than PNG_MAXDIM */
	PNG_ERR_MEMORY,
	PNG_ERR_DATA          /* image data could not be inflated or unfiltered */
};

typedef struct PngMem
{
	void *(*alloc)(void *ctx, uint32_t size);   /* need not be cleared */
	void  (*free)(void *ctx, void *p);
	void  *ctx;
} PngMem;

/* Inflate a zlib stream: exactly dstlen bytes must come out. 0 = success. */
typedef int (*png_inflate_fn)(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen);

/* Decode. On success *argb is a buffer from mem->alloc (free it with mem->free). */
int png_decode(const uint8_t *buf, uint32_t len, const PngMem *mem, png_inflate_fn inflate, void *ictx,
               uint8_t **argb, uint32_t *width, uint32_t *height);

/* CRC-32 (PNG/zlib polynomial); start with crc = 0. */
uint32_t png_crc32(uint32_t crc, const uint8_t *p, uint32_t n);

#endif
