/*
 * imagecache.c - default images and emblems (see imagecache.h).
 */
#include <exec/exec.h>
#include <dos/dos.h>
#include <dos/dostags.h>
#include <interfaces/exec.h>
#include <interfaces/dos.h>
#include <interfaces/utility.h>
#include <interfaces/z.h>
#include <libraries/z.h>

#include "imagecache.h"
#include "emblem.h"
#include "emblemspec.h"
#include "png.h"
#include "emblemprefs.h"

extern struct ExecIFace    *IExec;
extern struct DOSIFace     *IDOS;
extern struct UtilityIFace *IUtility;

#define RECHECK_TICKS 100   /* 2 seconds */

/* A scaled copy of an image (the same emblem at the same size in many icons). */
struct Scaled
{
	struct Scaled *next;
	uint32         w, h;
	uint8          px[];
};

#define MAXSCALED 8   /* scaled sizes kept per image */

struct CacheEntry
{
	struct MinNode   node;
	char             name[ES_NAMELEN];
	struct Scaled   *scaled;        /* newest first */
	uint8           *argb;          /* NULL: missing or broken file */
	uint32           width, height, bytes;
	struct DateStamp date;          /* file identity when it was read */
	int64            size;
	uint64           checked;       /* tick time of the last file check */
	uint64           lastuse;
};

static struct SignalSemaphore sem;
static struct MinList list;
static uint32 entries, totalbytes;
static uint64 usecount;

static CPPrefs prefs;
static BOOL prefsinit;
static uint64 prefschecked;
static struct DateStamp prefsdate;
static int64 prefssize;
static int prefsfrom;          /* 0 none, 1 ENV:, 2 ENVARC: */

static uint64 now_ticks(void)
{
	struct DateStamp ds;
	IDOS->DateStamp(&ds);
	return ((uint64)ds.ds_Days * 1440 + ds.ds_Minute) * 3000 + ds.ds_Tick;
}

void ic_init(void)
{
	IExec->InitSemaphore(&sem);
	IExec->NewMinList(&list);
	entries = totalbytes = 0;
}

static void drop_scaled(struct CacheEntry *e)
{
	struct Scaled *s, *next;
	for (s = e->scaled; s; s = next)
	{
		next = s->next;
		totalbytes -= s->w * s->h * 4;
		IExec->FreeVec(s);
	}
	e->scaled = NULL;
}

static void drop_pixels(struct CacheEntry *e)
{
	drop_scaled(e);
	if (e->argb)
	{
		IExec->FreeVec(e->argb);
		totalbytes -= e->bytes;
		e->argb = NULL;
		e->bytes = 0;
	}
}

void ic_cleanup(void)
{
	struct CacheEntry *e;
	while ((e = (struct CacheEntry *)IExec->RemHead((struct List *)&list)))
	{
		drop_pixels(e);
		IExec->FreeVec(e);
	}
	entries = 0;
}

void ic_prefs(CPPrefs *out)
{
	static CONST_STRPTR paths[2] = { EMBLEM_PREFS, EMBLEM_PREFSARC };
	uint64 now = now_ticks();

	if (!prefsinit)
	{
		ep_defaults(&prefs);
		prefsinit = TRUE;
		prefsfrom = 0;
		prefschecked = now - RECHECK_TICKS - 1;
	}
	if (now - prefschecked > RECHECK_TICKS || now < prefschecked)
	{
		struct ExamineData *ed = NULL;
		int from;
		prefschecked = now;
		for (from = 1; from <= 2; from++)
		{
			ed = IDOS->ExamineObjectTags(EX_StringNameInput, paths[from - 1], TAG_END);
			if (ed && EXD_IS_FILE(ed)) break;
			if (ed) IDOS->FreeDosObject(DOS_EXAMINEDATA, ed);
			ed = NULL;
		}
		if (!ed)
		{
			if (prefsfrom != 0) ep_defaults(&prefs);
			prefsfrom = 0;
		}
		else
		{
			if (from != prefsfrom || ed->FileSize != prefssize || IDOS->CompareDates(&ed->Date, &prefsdate) != 0)
			{
				char *buf = IExec->AllocVecTags(EP_MAXFILE, AVT_Type, MEMF_PRIVATE, TAG_DONE);
				int32 n = 0;
				BPTR fh = buf ? IDOS->Open(paths[from - 1], MODE_OLDFILE) : 0;
				if (fh)
				{
					n = IDOS->Read(fh, buf, EP_MAXFILE);
					IDOS->Close(fh);
				}
				ep_defaults(&prefs);
				if (n > 0) ep_parse(buf, (uint32)n, &prefs);
				if (buf) IExec->FreeVec(buf);
				prefsfrom = from;
				prefsdate = ed->Date;
				/* not read (no memory, file busy): try again at the next check */
				prefssize = (buf && fh) ? ed->FileSize : -1;
			}
			IDOS->FreeDosObject(DOS_EXAMINEDATA, ed);
		}
	}
	*out = prefs;
}

static void evict(struct CacheEntry *keep);

void ic_lock(void) { IExec->ObtainSemaphore(&sem); }

/* Eviction waits until here: pixels handed out inside lock/unlock stay valid. */
void ic_unlock(void)
{
	evict(NULL);
	IExec->ReleaseSemaphore(&sem);
}

static struct CacheEntry *find_entry(CONST_STRPTR name)
{
	struct CacheEntry *e;
	for (e = (struct CacheEntry *)list.mlh_Head; e->node.mln_Succ; e = (struct CacheEntry *)e->node.mln_Succ)
		if (IUtility->Stricmp(e->name, name) == 0)
			return e;
	return NULL;
}

const uint8 *ic_scaled_find(CONST_STRPTR name, uint32 w, uint32 h)
{
	struct CacheEntry *e = find_entry(name);
	struct Scaled *s;
	if (!e || !e->argb) return NULL;
	for (s = e->scaled; s; s = s->next)
		if (s->w == w && s->h == h) return s->px;
	return NULL;
}

void ic_scaled_store(CONST_STRPTR name, uint32 w, uint32 h, const uint8 *px)
{
	struct CacheEntry *e = find_entry(name);
	struct Scaled *s, **pp;
	uint32 n = 0;
	if (!e || !e->argb) return;
	if (!(s = IExec->AllocVecTags(sizeof(*s) + w * h * 4, AVT_Type, MEMF_PRIVATE, TAG_DONE))) return;
	s->w = w;
	s->h = h;
	IExec->CopyMem((APTR)px, s->px, w * h * 4);
	s->next = e->scaled;
	e->scaled = s;
	totalbytes += w * h * 4;
	/* keep the newest MAXSCALED sizes */
	for (pp = &e->scaled; *pp; pp = &(*pp)->next)
		if (++n == MAXSCALED)
		{
			struct Scaled *rest = (*pp)->next, *next;
			(*pp)->next = NULL;
			for (; rest; rest = next)
			{
				next = rest->next;
				totalbytes -= rest->w * rest->h * 4;
				IExec->FreeVec(rest);
			}
			break;
		}
}

static void *m_alloc(void *ctx, uint32_t size) { return IExec->AllocVecTags(size ? size : 1, AVT_Type, MEMF_PRIVATE, TAG_DONE); }
static void m_free(void *ctx, void *p) { IExec->FreeVec(p); }

static int z_inflate(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen)
{
	struct ZIFace *iz = ctx;
	uint32 n = dstlen;
	if (!iz || iz->Uncompress(dst, &n, src, srclen) != Z_OK || n != dstlen) return 1;
	return 0;
}

static void make_path(char *path, uint32 size, CONST_STRPTR name)
{
	CONST_STRPTR base = IDOS->FilePart(name), p;
	BOOL ext = FALSE;
	for (p = base; *p; p++)
		if (*p == '.') ext = TRUE;
	IUtility->Strlcpy(path, EMBLEM_IMAGEDIR, size);
	IUtility->Strlcat(path, name, size);
	if (!ext) IUtility->Strlcat(path, ".png", size);
}

/* (Re)read the file behind an entry; on any failure the entry stays "missing".
 * A broken or too large file is remembered (by date and size) and not read again
 * until it changes; a failure for lack of memory is not, so it is retried at the
 * next check. */
static void load(struct CacheEntry *e, CONST_STRPTR path, struct ExamineData *ed, struct ZIFace *iz)
{
	static const PngMem mem = { m_alloc, m_free, NULL };
	uint8_t *buf = NULL, *argb = NULL;
	uint32_t w = 0, h = 0;
	BOOL transient = FALSE;
	int r = PNG_ERR_FORMAT;
	BPTR fh = 0;

	drop_pixels(e);
	if (!iz)
		transient = TRUE;
	else if (ed->FileSize > 0 && ed->FileSize <= IC_MAXFILE)
	{
		if (!(fh = IDOS->Open(path, MODE_OLDFILE)))
			transient = TRUE;
		else if (!(buf = IExec->AllocVecTags((uint32)ed->FileSize, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
			transient = TRUE;
		else if (IDOS->Read(fh, buf, (uint32)ed->FileSize) != (int32)ed->FileSize)
			transient = TRUE;
		else if ((r = png_decode(buf, (uint32)ed->FileSize, &mem, z_inflate, iz, &argb, &w, &h)) == PNG_ERR_MEMORY)
			transient = TRUE;
	}
	if (r == PNG_OK)
	{
		e->argb   = argb;
		e->width  = w;
		e->height = h;
		e->bytes  = w * h * 4;
		totalbytes += e->bytes;
	}
	if (fh) IDOS->Close(fh);
	if (buf) IExec->FreeVec(buf);
	if (transient)
	{
		e->size = -1;          /* differs from any file: read again at the next check */
		return;
	}
	e->date = ed->Date;
	e->size = ed->FileSize;
}

static void evict(struct CacheEntry *keep)
{
	while (entries > IC_MAXENTRIES || totalbytes > IC_MAXBYTES)
	{
		struct CacheEntry *e, *old = NULL;
		for (e = (struct CacheEntry *)list.mlh_Head; e->node.mln_Succ; e = (struct CacheEntry *)e->node.mln_Succ)
			if (e != keep && (!old || e->lastuse < old->lastuse))
				old = e;
		if (!old) break;
		IExec->Remove((struct Node *)old);
		drop_pixels(old);
		IExec->FreeVec(old);
		entries--;
	}
}

const uint8 *ic_get(CONST_STRPTR name, uint32 *width, uint32 *height, struct ZIFace *iz)
{
	struct CacheEntry *e;
	uint64 now = now_ticks();

	for (e = (struct CacheEntry *)list.mlh_Head; e->node.mln_Succ; e = (struct CacheEntry *)e->node.mln_Succ)
		if (IUtility->Stricmp(e->name, name) == 0)
			break;
	if (!e->node.mln_Succ)
	{
		if (IUtility->Strlen(name) >= ES_NAMELEN) return NULL;
		if (!(e = IExec->AllocVecTags(sizeof(*e), AVT_Type, MEMF_PRIVATE, AVT_ClearWithValue, 0, TAG_DONE)))
			return NULL;
		IUtility->Strlcpy(e->name, name, sizeof(e->name));
		e->size = -1;
		e->checked = 0;
		IExec->AddTail((struct List *)&list, (struct Node *)e);
		entries++;
		e->checked = now - RECHECK_TICKS - 1;   /* check now */
	}

	if (now - e->checked > RECHECK_TICKS || now < e->checked)
	{
		char path[256];
		struct ExamineData *ed;
		make_path(path, sizeof(path), name);
		e->checked = now;
		ed = IDOS->ExamineObjectTags(EX_StringNameInput, path, TAG_END);
		if (!ed || !EXD_IS_FILE(ed))
		{
			drop_pixels(e);
			e->size = -1;
		}
		else if (ed->FileSize != e->size || IDOS->CompareDates(&ed->Date, &e->date) != 0 || !e->argb)
		{
			/* new or changed file (a broken one is retried only when it changes) */
			if (ed->FileSize != e->size || IDOS->CompareDates(&ed->Date, &e->date) != 0)
				load(e, path, ed, iz);
		}
		if (ed) IDOS->FreeDosObject(DOS_EXAMINEDATA, ed);
	}
	e->lastuse = ++usecount;
	if (!e->argb) return NULL;
	*width = e->width;
	*height = e->height;
	return e->argb;
}
