/*
 * emblemfile.h - Emblem icon file format (docs/format.md), portable C.
 *
 * Used by emblem.iconmodule (AmigaOS 4) and by the host tests. No Amiga
 * headers here: the caller converts between struct DiskObject and EFIcon.
 * Parsing is zero-copy: all pointers in a parsed EFIcon point into the
 * caller's file buffer, which must stay alive while the EFIcon is used.
 */
#ifndef EMBLEMFILE_H
#define EMBLEMFILE_H

#include <stdint.h>

#define EF_VERSION      1
#define EF_MAXDIM       256     /* icon.library's largest icon */
#define EF_MAXUNKNOWN   8       /* unknown chunks remembered by the parser */
#define EF_MINFILE      58      /* icon.library reads 58 bytes before asking modules */
#define EF_HEADPOS      12      /* file offset of HEAD's chunk header */
#define EF_POSOFFSET    32      /* file offset of do_CurrentX (then do_CurrentY) */

enum { EF_ARGB = 1, EF_CLUT = 2, EF_PLANAR = 3 };
enum { EF_RAW = 0, EF_ZLIB = 1 };

enum
{
	EF_OK = 0,
	EF_ERR_NOTEMBLEM,   /* not an Emblem file */
	EF_ERR_VERSION,     /* newer format version */
	EF_ERR_CORRUPT,     /* broken structure */
	EF_ERR_SPACE,       /* output buffer too small */
	EF_ERR_UNPACK       /* image data could not be decompressed */
};

typedef struct EFImage
{
	uint8_t        present;
	uint8_t        kind;          /* EF_ARGB, EF_CLUT, EF_PLANAR */
	uint16_t       width, height;
	/* EF_CLUT */
	uint16_t       palsize;
	int16_t        transparent;   /* -1 = none */
	const uint8_t *palette;       /* palsize * 3 bytes R,G,B */
	/* EF_PLANAR */
	int16_t        left, top;
	uint16_t       depth;
	uint8_t        planepick, planeonoff;
	/* pixels: uncompressed for ef_write(); as stored after ef_parse() */
	const uint8_t *data;
	uint32_t       datalen;       /* uncompressed length */
	uint8_t        comp;          /* after ef_parse(): EF_RAW or EF_ZLIB */
	uint32_t       complen;       /* after ef_parse(): stored length */
	const uint8_t *chunk;         /* after ef_parse(): the whole IMAG chunk (ID, length, data, pad) */
	uint32_t       chunklen;
} EFImage;

typedef struct EFChunk
{
	const uint8_t *data;          /* whole chunk: ID, length, data, pad */
	uint32_t       len;
} EFChunk;

typedef struct EFIcon
{
	uint8_t     type;
	uint8_t     frameless;
	uint8_t     aspect;
	uint16_t    gflags, gwidth, gheight;
	int32_t     curx, cury, stack;

	uint8_t     hasdrawer;
	int16_t     dleft, dtop, dwidth, dheight;
	int32_t     dcurx, dcury;
	uint32_t    dflags;
	uint16_t    dviewmodes;

	const char *deftool;          /* NULL = none; not NUL-terminated after parse */
	uint32_t    deftoollen;
	const char *toolwindow;       /* NULL = none */
	uint32_t    toolwindowlen;
	const char *tooltypes;        /* NULL = none; packed NUL-terminated strings */
	uint32_t    tooltypeslen;
	const char *settings;         /* ESET: the Emblem settings (IMAGE=, EMBLEM=, ...), packed
	                               * like the tool types; NULL = none */
	uint32_t    settingslen;

	EFImage     img[2];           /* chunky (ARGB/CLUT) images: [0] normal, [1] selected */
	EFImage     planar[2];        /* planar images: old icons, or the fallback of chunky icons */

	uint32_t    nunknown;
	EFChunk     unknown[EF_MAXUNKNOWN];
} EFIcon;

/* Compressor: compress src into dst (at most *dstlen bytes), set *dstlen.
 * Return 0 on success, non-zero if it failed or did not fit (data is then
 * stored raw). May be NULL: everything is stored raw. */
typedef int (*ef_compress_fn)(void *ctx, uint8_t *dst, uint32_t *dstlen,
                              const uint8_t *src, uint32_t srclen);
/* Decompressor: exactly dstlen bytes must come out. Return 0 on success. */
typedef int (*ef_uncompress_fn)(void *ctx, uint8_t *dst, uint32_t dstlen,
                                const uint8_t *src, uint32_t srclen);

/* Quick check of the first bytes (at least 24 needed). 1 = Emblem file. */
int ef_is_emblem(const uint8_t *buf, uint32_t len);

/* Total file size announced by the FORM header (0 if not an Emblem file). */
uint32_t ef_file_size(const uint8_t *buf, uint32_t len);

/* Parse a whole file. */
int ef_parse(const uint8_t *buf, uint32_t len, EFIcon *icon);

/* Parse one whole IMAG chunk (ID, length, data, as ef_parse() keeps it in img->chunk):
 * *state = 0 normal, 1 selected. Zero-copy like ef_parse(). */
int ef_parse_imag(const uint8_t *chunk, uint32_t len, EFImage *img, uint8_t *state);

/* Decompress (or copy) an image's stored data into dst (img->datalen bytes). */
int ef_image_unpack(const EFImage *img, uint8_t *dst, ef_uncompress_fn fn, void *ctx);

/* Expected uncompressed data length for an image's kind and size (0 = invalid). */
uint32_t ef_image_datalen(const EFImage *img);

/* Upper bound of the file size ef_write() can produce. */
uint32_t ef_write_bound(const EFIcon *icon);

/* Write the file into dst. img[].data must be uncompressed. */
int ef_write(const EFIcon *icon, uint8_t *dst, uint32_t dstmax, uint32_t *outlen,
             ef_compress_fn fn, void *ctx);

/* Number of strings in a packed block (tool types, settings). */
uint32_t ef_count_tooltypes(const char *tt, uint32_t len);

#endif
