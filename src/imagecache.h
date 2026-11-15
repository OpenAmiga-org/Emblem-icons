/*
 * imagecache.h - default images and emblems for emblem.iconmodule, decoded
 * from EMBLEM_IMAGEDIR and kept in memory.
 *
 * A name is checked against its file (date, size) at most every 2 seconds,
 * so new artwork shows on the next icon load after that. Missing and
 * broken files are remembered the same way. At most IC_MAXENTRIES images /
 * IC_MAXBYTES of pixels; the least recently used go first.
 */
#ifndef EMBLEM_IMAGECACHE_H
#define EMBLEM_IMAGECACHE_H

#include <exec/types.h>

struct ZIFace;

#define IC_MAXENTRIES 64
#define IC_MAXBYTES   (8 * 1024 * 1024)
#define IC_MAXFILE    (2 * 1024 * 1024)

void ic_init(void);
void ic_cleanup(void);

/* All ic_get() calls and the use of their pixels must be inside lock/unlock;
 * entries are only evicted at unlock. */
void ic_lock(void);
void ic_unlock(void);

struct CPPrefs;

/* The global settings (EMBLEM_PREFS, else EMBLEM_PREFSARC, else built in),
 * re-read when the file changes (checked at most every 2 seconds). */
void ic_prefs(struct CPPrefs *out);

/* Scaled copies of an image already got with ic_get() (inside the same lock). */
const uint8 *ic_scaled_find(CONST_STRPTR name, uint32 w, uint32 h);
void ic_scaled_store(CONST_STRPTR name, uint32 w, uint32 h, const uint8 *px);

/* ARGB pixels (A,R,G,B bytes) of the named image, or NULL if there is none.
 * iz may be NULL (then nothing new can be decoded). */
const uint8 *ic_get(CONST_STRPTR name, uint32 *width, uint32 *height, struct ZIFace *iz);

#endif
