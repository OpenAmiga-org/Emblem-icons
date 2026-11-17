/*
 * emblem.iconmodule - icon.library loader/saver module for Emblem icons.
 *
 * Loads and saves the Emblem file format (docs/format.md). On load, the
 * icon's settings (IMAGE=, IMAGESELECTED=, EMBLEM=, EMBLEMSELECTED=; the
 * file's ESET chunk, not its tool types) compose the displayed images from
 * default images and emblems in EMBLEM_IMAGEDIR (src/compose.c); saving
 * always writes the icon's own images and keeps the settings.
 * EMBLEMA_GetSettings and EMBLEMA_SetSettings (src/emblem.h) read and change
 * them.
 *
 * API: SDK workbench/iconmodule.h and AutoDocs/iconmodule.doc. The module
 * must not open icon.library itself; icon.library passes its interface
 * with IMA_SetIconIFace at startup.
 */

#include <exec/exec.h>
#include <exec/interfaces.h>
#include <exec/resident.h>
#include <dos/dos.h>
#include <intuition/intuition.h>
#include <workbench/workbench.h>
#include <workbench/icon.h>
#include <workbench/iconmodule.h>
#include <interfaces/iconmodule.h>
#include <interfaces/exec.h>
#include <interfaces/dos.h>
#include <interfaces/utility.h>
#include <interfaces/icon.h>
#include <interfaces/z.h>
#include <stdarg.h>

#include "emblemfile.h"
#include "emblemspec.h"
#include "compose.h"
#include "imagecache.h"
#include "png.h"
#include "emblem.h"
#include "emblem.iconmodule_rev.h"

#define LIBNAME   "emblem.iconmodule"
#define FORMAT    EMBLEM_FORMAT
#define MAXFILE   (4 * 1024 * 1024)

/* GCC 15: the SDK's va_getlinearva() passes &ap, the builtin wants the decayed va_list */
#define LINEARTAGS(ap) ((struct TagItem *)__builtin_getlinearva(ap))

static const char verstag[] __attribute__((used)) = VERSTAG;

#ifdef EMBLEM_PROFILE
/* Debug builds only (make os4-profile): time the phases of LoadIconA and print
 * averages to the debug buffer every 200 loads. */
#include <devices/timer.h>
#include <interfaces/timer.h>
static struct TimerIFace *ITimer;
static uint64 prof[12];
static uint32 profn;
static const char *profname[12] = { "read", "parse", "fill", "set_images", "compose", "cp_compose",
	"lock+prefs", "set_planar", "iconcontrol+fp", "md", "unpack", "total" };
static uint64 prof_now(void)
{
	struct TimeVal tv;
	ITimer->GetUpTime(&tv);
	return (uint64)tv.Seconds * 1000000 + tv.Microseconds;
}
#define PROF_START(v) uint64 v = ITimer ? prof_now() : 0
#define PROF_ADD(i, v) do { if (ITimer) prof[i] += prof_now() - (v); } while (0)
#else
#define PROF_START(v)
#define PROF_ADD(i, v)
#endif

struct EmblemBase
{
	struct Library         lib;
	BPTR                   seglist;
	struct SignalSemaphore zsem;
	BOOL                   ztried;
	struct Library        *ZBase;
	struct ZIFace         *IZ;
	uint32                 maxunknown;
};

/* Private data attached to every icon this module loads. The first
 * longword is our library base, as iconmodule.doc advises. */
struct EmblemData
{
	struct Library *owner;
	uint16          gwidth, gheight;  /* gadget size and flags from the file (layout changes them) */
	uint16          gflags;
	uint8           chunky;           /* the file had chunky images */
	uint8           composed;         /* the displayed images are composed, not the icon's own */
	uint8           has2;             /* the composed images include a selected one */
	uint8           pad[3];
	uint16          cw, ch;           /* composed size and CRCs: tell whether a client changed them */
	uint32          crc1, crc2;
	uint32          planarlen;        /* planar IMAG chunks of a chunky or composed icon */
	uint32          chunkylen;        /* chunky IMAG chunks of a composed icon */
	uint32          chunky0len;       /* ... of them the normal image's chunk (0 = none) */
	uint32          unknownlen;       /* unknown chunks */
	uint32          settingslen;      /* the settings (ESET), packed strings */
	uint8           data[];           /* planar, chunky, unknown chunks as in the file, settings */
};

/* What compose() did */
struct Composed
{
	BOOL   done;
	BOOL   has2;
	uint32 w, h, crc1, crc2;
};

struct ExecIFace    *IExec;
struct DOSIFace     *IDOS;
struct UtilityIFace *IUtility;
struct IconIFace    *IIcon;
static struct Library *DOSBase, *UtilityBase, *IconBase;

/* gcc may turn loops into these calls; there is no C library in a module */
void *memcpy(void *d, const void *s, unsigned long n)
{
	IExec->CopyMem((APTR)s, d, n);
	return d;
}
void *memmove(void *d, const void *s, unsigned long n)
{
	IExec->CopyMem((APTR)s, d, n);   /* CopyMem handles overlap on OS4 */
	return d;
}
void *memset(void *d, int c, unsigned long n)
{
	IUtility->SetMem(d, c, n);
	return d;
}

int32 _start(void) { return -1; }

static CONST_STRPTR FormatNames[] = { FORMAT, NULL };
static CONST_STRPTR FormatDescs[] = { "Emblem icon (default images and emblems)", NULL };

/* ---- helpers ---- */

static void set_error(struct TagItem *tags, int32 err)
{
	int32 *p = (int32 *)IUtility->GetTagData(IMA_ErrorCode, 0, tags);
	if (p) *p = err;
}

static struct ZIFace *get_z(struct EmblemBase *eb)
{
	IExec->ObtainSemaphore(&eb->zsem);
	if (!eb->ztried)
	{
		eb->ztried = TRUE;
		eb->ZBase = IExec->OpenLibrary("z.library", 53);
		if (eb->ZBase)
		{
			eb->IZ = (struct ZIFace *)IExec->GetInterface(eb->ZBase, "main", 1, NULL);
			if (!eb->IZ)
			{
				IExec->CloseLibrary(eb->ZBase);
				eb->ZBase = NULL;
			}
		}
	}
	IExec->ReleaseSemaphore(&eb->zsem);
	return eb->IZ;
}

static int z_compress(void *ctx, uint8_t *dst, uint32_t *dstlen, const uint8_t *src, uint32_t srclen)
{
	struct ZIFace *iz = ctx;
	uint32 n = *dstlen;
	if (!iz || iz->Compress2(dst, &n, src, srclen, 9) != Z_OK) return 1;
	*dstlen = n;
	return 0;
}

static int z_uncompress(void *ctx, uint8_t *dst, uint32_t dstlen, const uint8_t *src, uint32_t srclen)
{
	struct ZIFace *iz = ctx;
	uint32 n = dstlen;
	if (!iz || iz->Uncompress(dst, &n, src, srclen) != Z_OK || n != dstlen) return 1;
	return 0;
}

static struct EmblemData *our_data(struct EmblemBase *eb, struct DiskObject *icon)
{
	struct EmblemData *md = NULL;
	if (!icon) return NULL;
	if (IIcon->IconControl(icon, ICONCTRLA_GetIconModuleData, &md, TAG_DONE) != 1 || !md)
		return NULL;
	return md->owner == &eb->lib ? md : NULL;
}

static STRPTR fl_string(struct FreeList *fl, const char *s, uint32 len)
{
	STRPTR d = IIcon->FreeAlloc(fl, len + 1, MEMF_SHARED);
	if (d)
	{
		IExec->CopyMem((APTR)s, d, len);
		d[len] = 0;
	}
	return d;
}

static int32 ef_to_doserr(int r)
{
	switch (r)
	{
		case EF_ERR_NOTEMBLEM: return ERROR_OBJECT_WRONG_TYPE;
		case EF_ERR_VERSION:   return ERROR_BAD_NUMBER;
		case EF_ERR_SPACE:     return ERROR_NO_FREE_STORE;
		default:               return ERROR_BAD_HUNK;   /* "file is not an executable" -> best "corrupt" code */
	}
}

/* Read the whole file into a new buffer (FreeVec it). */
static uint8 *read_file(CONST_STRPTR name, uint32 *len, int32 *err)
{
	uint8 head[24], *buf = NULL;
	uint32 total;
	BPTR fh = IDOS->Open(name, MODE_OLDFILE);

	*err = 0;
	if (!fh)
	{
		*err = IDOS->IoErr();
		return NULL;
	}
	if (IDOS->Read(fh, head, sizeof(head)) != (int32)sizeof(head) || !ef_is_emblem(head, sizeof(head)))
		*err = ERROR_OBJECT_WRONG_TYPE;
	else if (!(total = ef_file_size(head, sizeof(head))) || total > MAXFILE)
		*err = ERROR_BAD_HUNK;
	else if (!(buf = IExec->AllocVecTags(total, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
		*err = ERROR_NO_FREE_STORE;
	else
	{
		IExec->CopyMem(head, buf, sizeof(head));
		if (IDOS->Read(fh, buf + sizeof(head), total - sizeof(head)) != (int32)(total - sizeof(head)))
		{
			*err = ERROR_BAD_HUNK;
			IExec->FreeVec(buf);
			buf = NULL;
		}
		else
			*len = total;
	}
	IDOS->Close(fh);
	return buf;
}

/* ---- loading: EFIcon -> DiskObject ---- */

/* The icon's own image i (0 normal, 1 selected) as ARGB, or NULL. own[] are the
 * unpacked chunky images, pl[] the unpacked planar ones of planar-only icons. */
/* The icon's own images, unpacked the first time they are needed: with IMAGE= and
 * IMAGESELECTED= a composed icon usually never needs them. */
struct OwnImages
{
	struct FreeList *fl;
	const EFIcon    *ef;
	struct ZIFace   *iz;
	BOOL             tried[2], pltried[2];
	uint8           *d[2], *pl[2];
	BOOL             failed;     /* an image could not be unpacked */
};

static uint8 *unpack(struct OwnImages *o, const EFImage *img)
{
	uint8 *d;
	PROF_START(tu);
	if (!(d = IIcon->FreeAlloc(o->fl, img->datalen, MEMF_SHARED))
		|| ef_image_unpack(img, d, z_uncompress, o->iz) != EF_OK)
	{
		o->failed = TRUE;
		d = NULL;
	}
	PROF_ADD(10, tu);
	return d;
}

static uint8 *own_chunky(struct OwnImages *o, int i)
{
	if (!o->tried[i])
	{
		o->tried[i] = TRUE;
		if (o->ef->img[i].present) o->d[i] = unpack(o, &o->ef->img[i]);
	}
	return o->d[i];
}

static uint8 *own_planar(struct OwnImages *o, int i)
{
	if (!o->pltried[i])
	{
		o->pltried[i] = TRUE;
		if (o->ef->planar[i].present) o->pl[i] = unpack(o, &o->ef->planar[i]);
	}
	return o->pl[i];
}

/* The icon's own image i (0 normal, 1 selected) as ARGB, or NULL: its chunky
 * image, or for planar-only icons its planar one. */
static uint8 *own_argb(struct OwnImages *o, int i, uint32 *w, uint32 *h)
{
	const EFIcon *ef = o->ef;
	const EFImage *img = &ef->img[i];
	uint8 *d, *src;
	if (img->present && (src = own_chunky(o, i)))
	{
		*w = img->width;
		*h = img->height;
		if (img->kind == EF_ARGB) return src;
		if (!(d = IIcon->FreeAlloc(o->fl, img->width * img->height * 4, MEMF_SHARED))) return NULL;
		cp_from_clut(d, src, img->width * img->height, img->palette, img->palsize, img->transparent);
		return d;
	}
	img = &ef->planar[i];
	if (!ef->img[0].present && img->present && (src = own_planar(o, i)))
	{
		*w = img->width;
		*h = img->height;
		if (!(d = IIcon->FreeAlloc(o->fl, img->width * img->height * 4, MEMF_SHARED))) return NULL;
		cp_from_planar(d, img->width, img->height, src, img->depth);
		return d;
	}
	return NULL;
}

/* Image source for cp_compose(): default images/emblems from the cache, the
 * icon's own images converted to ARGB the first time they are asked for. */
struct GetCtx
{
	struct OwnImages *own;
	struct ZIFace    *iz;
	BOOL              tried[2];
	uint8            *argb[2];
	uint32            w[2], h[2];
};

static int get_image(void *ctx, const char *name, int o, CPImage *img)
{
	struct GetCtx *g = ctx;
	if (!name)
	{
		if (!g->tried[o])
		{
			g->tried[o] = TRUE;
			g->argb[o] = own_argb(g->own, o, &g->w[o], &g->h[o]);
		}
		if (!g->argb[o]) return 0;
		img->px = g->argb[o];
		img->w  = g->w[o];
		img->h  = g->h[o];
		return 1;
	}
	{
		uint32 w = 0, h = 0;
		const uint8 *px = ic_get(name, &w, &h, g->iz);
		if (!px) return 0;
		img->px = px;
		img->w  = w;
		img->h  = h;
		return 1;
	}
}

/* A cheap fingerprint of composed images (Fletcher-like over longwords): only
 * tells whether a program replaced them before saving, so no CRC is needed. */
static uint32 fingerprint(const uint8 *px, uint32 bytes)
{
	const uint32 *w = (const uint32 *)px;
	uint32 a = 1, b = 0, n = bytes / 4;
	while (n--)
	{
		a += *w++;
		b += a;
	}
	return (b << 7 | b >> 25) ^ a;
}

static const uint8_t *sc_find(void *ctx, const char *name, uint32_t w, uint32_t h) { return ic_scaled_find(name, w, h); }
static void sc_store(void *ctx, const char *name, uint32_t w, uint32_t h, const uint8_t *px) { ic_scaled_store(name, w, h, px); }
static const CPScaleCache scalecache = { sc_find, sc_store, NULL };

static void *fl_alloc(void *ctx, uint32_t size) { return IIcon->FreeAlloc((struct FreeList *)ctx, size, MEMF_SHARED); }
static void *tmp_alloc(void *ctx, uint32_t size) { return IExec->AllocVecTags(size ? size : 1, AVT_Type, MEMF_PRIVATE, TAG_DONE); }
static void tmp_free(void *ctx, void *p) { IExec->FreeVec(p); }

/* IMAGE=, IMAGESELECTED=, EMBLEM=, EMBLEMSELECTED= (src/compose.c does the work).
 * Returns FALSE (icon untouched) if there is nothing to compose. */
static BOOL compose(struct EmblemBase *eb, struct DiskObject *icon, struct FreeList *fl,
	const ESpec *spec, struct OwnImages *own, struct Composed *c)
{
	struct GetCtx g;
	CPMem out = { fl_alloc, NULL, fl }, tmp = { tmp_alloc, tmp_free, NULL };
	CPResult res;
	CPPrefs prefs;
	int r;

	IUtility->SetMem(&g, 0, sizeof(g));
	g.own = own;
	g.iz  = get_z(eb);
	{
	PROF_START(t0);
	ic_lock();
	ic_prefs(&prefs);
	PROF_ADD(6, t0);
	}
	{
	PROF_START(t1);
	r = cp_compose(spec, &prefs, get_image, &g, &out, &tmp, &scalecache, &res);
	PROF_ADD(5, t1);
	}
	ic_unlock();
	if (r != 1) return FALSE;
	PROF_START(t2);

	IIcon->IconControl(icon,
		ICONCTRLA_SetImageDataFormat, IDFMT_DIRECTMAPPED,
		ICONCTRLA_SetWidth,           res.w,
		ICONCTRLA_SetHeight,          res.h,
		ICONCTRLA_SetImageData1,      res.img[0],
		TAG_DONE);
	if (res.img[1])
		IIcon->IconControl(icon, ICONCTRLA_SetImageData2, res.img[1], TAG_DONE);
	c->done = TRUE;
	c->has2 = res.img[1] != NULL;
	c->w    = res.w;
	c->h    = res.h;
	c->crc1 = fingerprint(res.img[0], res.w * res.h * 4);
	c->crc2 = res.img[1] ? fingerprint(res.img[1], res.w * res.h * 4) : 0;
	PROF_ADD(8, t2);
	return TRUE;
}

static BOOL set_images(struct EmblemBase *eb, struct DiskObject *icon, struct FreeList *fl, const EFIcon *ef,
	const ESpec *spec, struct Composed *c)
{
	const EFImage *a = &ef->img[0], *b = &ef->img[1];
	struct OwnImages own;
	uint8 *d[2];
	int i;

	IUtility->SetMem(&own, 0, sizeof(own));
	own.fl = fl;
	own.ef = ef;
	if (a->comp == EF_ZLIB || (b->present && b->comp == EF_ZLIB)
		|| ef->planar[0].comp == EF_ZLIB || (ef->planar[1].present && ef->planar[1].comp == EF_ZLIB))
		if (!(own.iz = get_z(eb))) return FALSE;

	{
	PROF_START(tc);
	BOOL done = spec && compose(eb, icon, fl, spec, &own, c);
	PROF_ADD(4, tc);
	if (done) return TRUE;
	}
	if (!a->present) return TRUE;

	/* not composed: the icon shows its own images */
	for (i = 0; i < 2; i++)
	{
		d[i] = own_chunky(&own, i);
		if (own.failed) return FALSE;
	}

	if (a->kind == EF_ARGB)
	{
		IIcon->IconControl(icon,
			ICONCTRLA_SetImageDataFormat, IDFMT_DIRECTMAPPED,
			ICONCTRLA_SetWidth,           a->width,
			ICONCTRLA_SetHeight,          a->height,
			ICONCTRLA_SetImageData1,      d[0],
			TAG_DONE);
		if (d[1])
			IIcon->IconControl(icon, ICONCTRLA_SetImageData2, d[1], TAG_DONE);
	}
	else if (a->kind == EF_CLUT)
	{
		struct ColorRegister *pal[2] = { NULL, NULL };
		for (i = 0; i < 2; i++)
		{
			const EFImage *img = &ef->img[i];
			if (!img->present) continue;
			if (!(pal[i] = IIcon->FreeAlloc(fl, img->palsize * 3, MEMF_SHARED))) return FALSE;
			IExec->CopyMem((APTR)img->palette, pal[i], img->palsize * 3);
		}
		IIcon->IconControl(icon,
			ICONCTRLA_SetImageDataFormat, IDFMT_PALETTEMAPPED,
			ICONCTRLA_SetWidth,           a->width,
			ICONCTRLA_SetHeight,          a->height,
			ICONCTRLA_SetPaletteSize1,    a->palsize,
			ICONCTRLA_SetPalette1,        pal[0],
			ICONCTRLA_SetTransparentColor1, (int32)a->transparent,
			ICONCTRLA_SetImageData1,      d[0],
			TAG_DONE);
		if (d[1])
			IIcon->IconControl(icon,
				ICONCTRLA_SetPaletteSize2,    b->palsize,
				ICONCTRLA_SetPalette2,        pal[1],
				ICONCTRLA_SetTransparentColor2, (int32)b->transparent,
				ICONCTRLA_SetImageData2,      d[1],
				TAG_DONE);
	}
	return TRUE;
}

static struct Image *new_image(struct FreeList *fl, uint16 w, uint16 h, uint16 depth, uint8 pick,
	uint8 onoff, int16 left, int16 top, UWORD *data)
{
	struct Image *im = IIcon->FreeAlloc(fl, sizeof(struct Image), MEMF_SHARED | MEMF_CLEAR);
	if (im)
	{
		im->LeftEdge   = left;
		im->TopEdge    = top;
		im->Width      = w;
		im->Height     = h;
		im->Depth      = depth;
		im->ImageData  = data;
		im->PlanePick  = pick;
		im->PlaneOnOff = onoff;
	}
	return im;
}

static struct Image *load_planar(struct FreeList *fl, const EFImage *img, struct ZIFace *iz)
{
	uint8 *d = IIcon->FreeAlloc(fl, img->datalen, MEMF_SHARED);
	if (!d || ef_image_unpack(img, d, z_uncompress, iz) != EF_OK) return NULL;
	return new_image(fl, img->width, img->height, img->depth, img->planepick, img->planeonoff,
		img->left, img->top, (UWORD *)d);
}

/* A 4-colour planar fallback built from chunky pixels, for icons whose file has
 * none: icon.library needs one to duplicate an icon or save it natively.
 * Workbench pens: 0 background (transparent), 1 black, 2 white, 3 blue. */
static struct Image *make_fallback(struct FreeList *fl, const EFImage *img, const uint8 *px)
{
	uint32 words = (img->width + 15) / 16, plane = words * img->height, x, y;
	UWORD *data = IIcon->FreeAlloc(fl, plane * 2 * sizeof(UWORD), MEMF_SHARED | MEMF_CLEAR);
	if (!data) return NULL;
	for (y = 0; y < img->height; y++)
		for (x = 0; x < img->width; x++)
		{
			uint32 i = y * img->width + x, a, r, g, b, lum, col;
			if (img->kind == EF_ARGB)
			{
				a = px[i * 4]; r = px[i * 4 + 1]; g = px[i * 4 + 2]; b = px[i * 4 + 3];
			}
			else
			{
				uint8 c = px[i];
				a = (c == img->transparent || c >= img->palsize) ? 0 : 255;
				r = img->palette[c * 3]; g = img->palette[c * 3 + 1]; b = img->palette[c * 3 + 2];
			}
			if (a < 128) continue;
			lum = (r * 3 + g * 6 + b) / 10;
			col = lum < 85 ? 1 : lum > 170 ? 2 : 3;
			if (col & 1) data[y * words + x / 16] |= 0x8000 >> (x & 15);
			if (col & 2) data[plane + y * words + x / 16] |= 0x8000 >> (x & 15);
		}
	return new_image(fl, img->width, img->height, 2, 3, 0, 0, 0, data);
}

/* Planar images: from the file, else (chunky or composed icons) a fallback. Call after set_images(). */
static BOOL set_planar(struct EmblemBase *eb, struct DiskObject *icon, struct FreeList *fl, const EFIcon *ef,
	const struct Composed *c)
{
	struct Image *im[2] = { NULL, NULL };
	struct ZIFace *iz = NULL;
	struct Gadget *g = &icon->do_Gadget;
	int i;

	if (ef->planar[0].present)
	{
		if ((ef->planar[0].comp == EF_ZLIB || (ef->planar[1].present && ef->planar[1].comp == EF_ZLIB))
			&& !(iz = get_z(eb)))
			return FALSE;
		for (i = 0; i < 2; i++)
			if (ef->planar[i].present && !(im[i] = load_planar(fl, &ef->planar[i], iz)))
				return FALSE;
	}
	else if (c->done)
	{
		EFImage cur;
		uint8 *d1 = NULL, *d2 = NULL;
		IUtility->SetMem(&cur, 0, sizeof(cur));
		cur.kind   = EF_ARGB;
		cur.width  = c->w;
		cur.height = c->h;
		IIcon->IconControl(icon, ICONCTRLA_GetImageData1, &d1, ICONCTRLA_GetImageData2, &d2, TAG_DONE);
		if (d1 && !(im[0] = make_fallback(fl, &cur, d1))) return FALSE;
		if (im[0] && c->has2 && d2 && !(im[1] = make_fallback(fl, &cur, d2))) return FALSE;
	}
	else if (ef->img[0].present)
	{
		uint8 *d1 = NULL, *d2 = NULL;
		IIcon->IconControl(icon, ICONCTRLA_GetImageData1, &d1, ICONCTRLA_GetImageData2, &d2, TAG_DONE);
		if (d1 && !(im[0] = make_fallback(fl, &ef->img[0], d1))) return FALSE;
		if (im[0] && ef->img[1].present && d2 && !(im[1] = make_fallback(fl, &ef->img[1], d2))) return FALSE;
	}
	if (!im[0] && !ef->img[0].present && !c->done)
	{
		/* No image at all (a broken or odd file): icon.library crashes on an icon
		 * without one, so give it a 16x16 frame. */
		UWORD *data = IIcon->FreeAlloc(fl, 16 * 2 * sizeof(UWORD), MEMF_SHARED | MEMF_CLEAR);
		int y;
		if (!data) return FALSE;
		for (y = 0; y < 16; y++) data[y] = (y == 0 || y == 15) ? 0xFFFF : 0x8001;
		if (!(im[0] = new_image(fl, 16, 16, 2, 3, 0, 0, 0, data))) return FALSE;
		g->Flags = (g->Flags & ~GFLG_GADGHIGHBITS) | GFLG_GADGHCOMP;
		if (!g->Width || g->Width > 1024)  g->Width  = 16;
		if (!g->Height || g->Height > 1024) g->Height = 16;
	}
	if (!ef->img[0].present && !c->done)
		IIcon->IconControl(icon, ICONCTRLA_SetImageDataFormat, IDFMT_BITMAPPED, TAG_DONE);

	g->GadgetRender = im[0];
	g->SelectRender = im[1];
	if (im[0])
	{
		g->Flags |= GFLG_GADGIMAGE;
		if (!g->Width)  g->Width  = im[0]->Width;
		if (!g->Height) g->Height = im[0]->Height;
	}
	if (!im[1] && (g->Flags & GFLG_GADGHIGHBITS) == GFLG_GADGHIMAGE)
		g->Flags = (g->Flags & ~GFLG_GADGHIGHBITS) | GFLG_GADGHCOMP;
	return TRUE;
}

/* The settings in md as a NULL-terminated array on fl (pointing into md); NULL if none. */
static STRPTR *settings_array(struct FreeList *fl, struct EmblemData *md)
{
	char *s = (char *)md->data + md->planarlen + md->chunkylen + md->unknownlen;
	uint32 n = ef_count_tooltypes(s, md->settingslen), i, k = 0;
	STRPTR *a;
	if (!n || !(a = IIcon->FreeAlloc(fl, (n + 1) * sizeof(STRPTR), MEMF_SHARED | MEMF_CLEAR)))
		return NULL;
	for (i = 0; i < md->settingslen && k < n; )
	{
		a[k++] = s + i;
		while (i < md->settingslen && s[i]) i++;
		i++;
	}
	return a;
}

static int32 fill_icon(struct EmblemBase *eb, struct DiskObject *icon, struct FreeList *fl, const EFIcon *ef,
	BOOL nocompose, STRPTR **getsettings)
{
	struct EmblemData *md;
	struct Gadget *g = &icon->do_Gadget;
	struct Composed c = { FALSE, FALSE, 0, 0, 0, 0 };
	ESpec spec;
	const ESpec *sp = NULL;
	uint32 i, unknownlen = 0, planarlen = 0, chunkylen = 0;

	/* The "empty" DiskObject icon.library passes is not cleared: set every field. */
	icon->do_Magic       = WB_DISKMAGIC;
	icon->do_Version     = WB_DISKVERSION;
	icon->do_Type        = ef->type;
	icon->do_DefaultTool = NULL;
	icon->do_ToolTypes   = NULL;
	icon->do_CurrentX    = ef->curx;
	icon->do_CurrentY    = ef->cury;
	icon->do_DrawerData  = NULL;
	icon->do_ToolWindow  = NULL;
	icon->do_StackSize   = ef->stack;
	g->NextGadget    = NULL;
	g->LeftEdge      = 0;
	g->TopEdge       = 0;
	g->Width         = ef->gwidth;
	g->Height        = ef->gheight;
	g->Flags         = ef->gflags;
	g->Activation    = GACT_RELVERIFY | GACT_IMMEDIATE;   /* what native icons carry */
	g->GadgetType    = GTYP_BOOLGADGET;
	g->GadgetRender  = NULL;
	g->SelectRender  = NULL;
	g->GadgetText    = NULL;
	g->MutualExclude = 0;
	g->SpecialInfo   = NULL;
	g->GadgetID      = 0;
	g->UserData      = (APTR)WB_DISKREVISION;

	if (ef->deftool && !(icon->do_DefaultTool = fl_string(fl, ef->deftool, ef->deftoollen)))
		return ERROR_NO_FREE_STORE;
	if (ef->toolwindow && !(icon->do_ToolWindow = fl_string(fl, ef->toolwindow, ef->toolwindowlen)))
		return ERROR_NO_FREE_STORE;
	if (ef->tooltypes)
	{
		uint32 n = ef_count_tooltypes(ef->tooltypes, ef->tooltypeslen), k = 0;
		STRPTR *tt = IIcon->FreeAlloc(fl, (n + 1) * sizeof(STRPTR), MEMF_SHARED | MEMF_CLEAR);
		STRPTR s = n ? IIcon->FreeAlloc(fl, ef->tooltypeslen, MEMF_SHARED) : NULL;
		if (!tt || (n && !s)) return ERROR_NO_FREE_STORE;
		if (n) IExec->CopyMem((APTR)ef->tooltypes, s, ef->tooltypeslen);
		for (i = 0; i < ef->tooltypeslen && k < n; )
		{
			tt[k++] = s + i;
			while (i < ef->tooltypeslen && s[i]) i++;
			i++;
		}
		icon->do_ToolTypes = tt;
	}
	if (ef->hasdrawer)
	{
		struct DrawerData *dd = IIcon->FreeAlloc(fl, sizeof(struct DrawerData), MEMF_SHARED | MEMF_CLEAR);
		if (!dd) return ERROR_NO_FREE_STORE;
		dd->dd_NewWindow.LeftEdge = ef->dleft;
		dd->dd_NewWindow.TopEdge  = ef->dtop;
		dd->dd_NewWindow.Width    = ef->dwidth;
		dd->dd_NewWindow.Height   = ef->dheight;
		dd->dd_CurrentX           = ef->dcurx;
		dd->dd_CurrentY           = ef->dcury;
		dd->dd_Flags              = ef->dflags;
		dd->dd_ViewModes          = ef->dviewmodes;
		icon->do_DrawerData = dd;
	}
	else if (ef->type == WBDISK || ef->type == WBDRAWER || ef->type == WBGARBAGE)
	{
		/* Workbench refuses to open a drawer whose icon has no drawer data:
		 * give it the default one (the box of def_disk), show/view by default */
		struct DrawerData *dd = IIcon->FreeAlloc(fl, sizeof(struct DrawerData), MEMF_SHARED | MEMF_CLEAR);
		if (!dd) return ERROR_NO_FREE_STORE;
		dd->dd_NewWindow.LeftEdge = 50;
		dd->dd_NewWindow.TopEdge  = 50;
		dd->dd_NewWindow.Width    = 400;
		dd->dd_NewWindow.Height   = 100;
		icon->do_DrawerData = dd;
	}

	if (!nocompose && ef->settings && es_parse(ef->settings, ef->settingslen, &spec))
		sp = &spec;
	{
	PROF_START(ts);
	if (!set_images(eb, icon, fl, ef, sp, &c)) return ERROR_NO_FREE_STORE;
	PROF_ADD(3, ts);
	}
	{
	PROF_START(tp);
	if (!set_planar(eb, icon, fl, ef, &c)) return ERROR_NO_FREE_STORE;
	PROF_ADD(7, tp);
	}
	PROF_START(tm);
	IIcon->IconControl(icon,
		ICONCTRLA_SetFrameless,   ef->frameless ? TRUE : FALSE,
		ICONCTRLA_SetAspectRatio, ef->aspect,
		TAG_DONE);

	/* Keep the file's own image chunks with the icon: the planar ones of a chunky icon
	 * (once Workbench has laid the icon out, GadgetRender holds a screen-remapped copy)
	 * and, when the displayed images are composed, all of them. */
	for (i = 0; i < 2; i++)
	{
		if (ef->planar[i].present && (ef->img[0].present || c.done)) planarlen += ef->planar[i].chunklen;
		if (ef->img[i].present && c.done) chunkylen += ef->img[i].chunklen;
	}
	for (i = 0; i < ef->nunknown; i++)
		if (unknownlen + ef->unknown[i].len <= eb->maxunknown)
			unknownlen += ef->unknown[i].len;
	if (!(md = IIcon->FreeAlloc(fl, sizeof(*md) + planarlen + chunkylen + unknownlen + ef->settingslen,
		MEMF_SHARED | MEMF_CLEAR)))
		return ERROR_NO_FREE_STORE;
	md->owner    = &eb->lib;
	md->gwidth   = ef->gwidth;
	md->gheight  = ef->gheight;
	md->gflags   = ef->gflags;
	md->chunky   = ef->img[0].present ? 1 : 0;
	md->composed = c.done ? 1 : 0;
	md->has2     = c.has2 ? 1 : 0;
	md->cw       = c.w;
	md->ch       = c.h;
	md->crc1     = c.crc1;
	md->crc2     = c.crc2;
	md->planarlen  = planarlen;
	md->chunkylen  = chunkylen;
	planarlen = chunkylen = 0;
	for (i = 0; i < 2; i++)
		if (ef->planar[i].present && (ef->img[0].present || c.done))
		{
			IExec->CopyMem((APTR)ef->planar[i].chunk, md->data + planarlen, ef->planar[i].chunklen);
			planarlen += ef->planar[i].chunklen;
		}
	for (i = 0; i < 2; i++)
		if (ef->img[i].present && c.done)
		{
			IExec->CopyMem((APTR)ef->img[i].chunk, md->data + md->planarlen + chunkylen, ef->img[i].chunklen);
			chunkylen += ef->img[i].chunklen;
			if (i == 0) md->chunky0len = ef->img[0].chunklen;
		}
	for (i = 0, unknownlen = 0; i < ef->nunknown; i++)
		if (unknownlen + ef->unknown[i].len <= eb->maxunknown)
		{
			IExec->CopyMem((APTR)ef->unknown[i].data, md->data + md->planarlen + md->chunkylen + unknownlen,
				ef->unknown[i].len);
			unknownlen += ef->unknown[i].len;
		}
	md->unknownlen = unknownlen;
	if (ef->settings && ef->settingslen)
	{
		IExec->CopyMem((APTR)ef->settings, md->data + md->planarlen + md->chunkylen + unknownlen, ef->settingslen);
		md->settingslen = ef->settingslen;
	}
	IIcon->IconControl(icon, ICONCTRLA_SetIconModuleData, md, TAG_DONE);
	if (getsettings) *getsettings = md->settingslen ? settings_array(fl, md) : NULL;
	PROF_ADD(9, tm);
	return 0;
}

/* ---- saving: DiskObject -> EFIcon ---- */

struct SaveBuf
{
	char  *tooltypes;     /* packed tool types (AllocVec) */
	char  *settings;      /* packed settings from EMBLEMA_SetSettings (AllocVec) */
	uint8 *own;           /* an own image of the file, unpacked (AllocVec) */
};

/* Pack a NULL-terminated string array (empty strings left out) into *buf
 * (AllocVec); *len = 0 and no buffer if there is nothing. FALSE: no memory. */
static BOOL pack_strings(STRPTR *a, char **buf, uint32_t *len)
{
	uint32 n = 0, pos = 0, i;
	*buf = NULL;
	*len = 0;
	for (i = 0; a && a[i]; i++)
		if (a[i][0]) n += IUtility->Strlen(a[i]) + 1;
	if (!n) return TRUE;
	if (!(*buf = IExec->AllocVecTags(n, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
		return FALSE;
	for (i = 0; a[i]; i++)
		if (a[i][0])
		{
			uint32 l = IUtility->Strlen(a[i]) + 1;
			IExec->CopyMem(a[i], *buf + pos, l);
			pos += l;
		}
	*len = pos;
	return TRUE;
}

static void get_planar(const struct Image *im, EFImage *img)
{
	if (!im || !im->ImageData || im->Width < 1 || im->Height < 1 || im->Depth < 1 || im->Depth > 8)
		return;
	img->present    = 1;
	img->kind       = EF_PLANAR;
	img->width      = im->Width;
	img->height     = im->Height;
	img->left       = im->LeftEdge;
	img->top        = im->TopEdge;
	img->depth      = im->Depth;
	img->planepick  = im->PlanePick;
	img->planeonoff = im->PlaneOnOff;
	img->data       = (const uint8_t *)im->ImageData;
	img->datalen    = ef_image_datalen(img);
	if (!img->datalen) img->present = 0;
}

/* A program changed one of the two composed images (pasted a new picture, deleted the
 * selected one) and left the other: that one is still the composed picture, so the file's
 * own image goes in its place. keep = the unchanged one (0 normal, 1 selected); ef->img[]
 * hold the program's images. FALSE if they can't be put together (the own image isn't a
 * chunky one, or kind or size differ): the caller then takes both images as they are. */
static BOOL keep_own(struct EmblemBase *eb, struct EmblemData *md, EFIcon *ef, struct SaveBuf *sb, int keep)
{
	const uint8 *chunks = md->data + md->planarlen;
	uint32 off = keep ? md->chunky0len : 0;
	uint32 len = keep ? md->chunkylen - md->chunky0len : md->chunky0len;
	EFImage own, *other = &ef->img[1 - keep];
	uint8_t state;

	if (!len)
	{
		/* no own image in that place: only a missing own selected image is fine */
		if (!keep || !ef->img[0].present) return FALSE;
		ef->img[1].present = 0;
	}
	else
	{
		if (ef_parse_imag(chunks + off, len, &own, &state) != EF_OK || state != keep || own.kind == EF_PLANAR)
			return FALSE;
		if (other->present && (other->kind != own.kind || other->width != own.width || other->height != own.height))
			return FALSE;
		if (keep == 1 && !other->present) return FALSE;
		if (own.comp != EF_RAW)
		{
			if (!(sb->own = IExec->AllocVecTags(own.datalen, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
				return FALSE;
			if (ef_image_unpack(&own, sb->own, z_uncompress, get_z(eb)) != EF_OK) return FALSE;
			own.data = sb->own;
			own.comp = EF_RAW;
		}
		ef->img[keep] = own;
	}
	/* no planar images: the module makes a fallback when it loads the icon */
	ef->planar[0].present = ef->planar[1].present = 0;
	ef->gwidth  = ef->img[0].width;
	ef->gheight = ef->img[0].height;
	ef->gflags  = (ef->gflags & ~GFLG_GADGHIGHBITS) | (ef->img[1].present ? GFLG_GADGHIMAGE : GFLG_GADGHCOMP);
	return TRUE;
}

/* setsettings: the EMBLEMA_SetSettings tag, or NULL to keep the icon's own settings;
 * dropplanar: ICONPUTA_DropPlanarIconImage (the Information window's "Drop planar data"):
 * an icon with chunky images is saved without its planar fallback (made again at load) */
static int32 icon_to_ef(struct EmblemBase *eb, struct DiskObject *icon, EFIcon *ef, struct SaveBuf *sb,
	struct TagItem *setsettings, BOOL dropplanar)
{
	struct EmblemData *md;
	uint32 fmt = IDFMT_BITMAPPED, frameless = 0, i, w = 0, h = 0;
	int32 real2 = FALSE;
	uint8 *d1 = NULL, *d2 = NULL, aspect = 0;

	IUtility->SetMem(ef, 0, sizeof(*ef));
	ef->img[0].transparent = ef->img[1].transparent = -1;
	ef->type    = icon->do_Type;
	ef->curx    = icon->do_CurrentX;
	ef->cury    = icon->do_CurrentY;
	ef->stack   = icon->do_StackSize;
	ef->gflags  = icon->do_Gadget.Flags;
	ef->gwidth  = icon->do_Gadget.Width;
	ef->gheight = icon->do_Gadget.Height;

	IIcon->IconControl(icon, ICONCTRLA_GetFrameless, &frameless, ICONCTRLA_GetAspectRatio, &aspect, TAG_DONE);
	ef->frameless = frameless ? 1 : 0;
	/* PACK_ICON_ASPECT_RATIO(num, den): a 0 in either half is no ratio (the Information
	 * window's Restore leaves 0x40 on an icon), so it is stored as unknown */
	ef->aspect    = (aspect >> 4) && (aspect & 15) ? aspect : ICON_ASPECT_RATIO_UNKNOWN;

	if (icon->do_DefaultTool)
	{
		ef->deftool    = (const char *)icon->do_DefaultTool;
		ef->deftoollen = IUtility->Strlen(icon->do_DefaultTool);
	}
	if (icon->do_ToolWindow)
	{
		ef->toolwindow    = (const char *)icon->do_ToolWindow;
		ef->toolwindowlen = IUtility->Strlen(icon->do_ToolWindow);
	}
	if (icon->do_ToolTypes)
	{
		uint32 len = 0, pos = 0;
		for (i = 0; icon->do_ToolTypes[i]; i++) len += IUtility->Strlen(icon->do_ToolTypes[i]) + 1;
		if (!(sb->tooltypes = IExec->AllocVecTags(len + 1, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
			return ERROR_NO_FREE_STORE;
		for (i = 0; icon->do_ToolTypes[i]; i++)
		{
			uint32 l = IUtility->Strlen(icon->do_ToolTypes[i]) + 1;
			IExec->CopyMem(icon->do_ToolTypes[i], sb->tooltypes + pos, l);
			pos += l;
		}
		ef->tooltypes    = sb->tooltypes;
		ef->tooltypeslen = pos;
	}
	if (icon->do_DrawerData)
	{
		struct DrawerData *dd = icon->do_DrawerData;
		ef->hasdrawer  = 1;
		ef->dleft      = dd->dd_NewWindow.LeftEdge;
		ef->dtop       = dd->dd_NewWindow.TopEdge;
		ef->dwidth     = dd->dd_NewWindow.Width;
		ef->dheight    = dd->dd_NewWindow.Height;
		ef->dcurx      = dd->dd_CurrentX;
		ef->dcury      = dd->dd_CurrentY;
		ef->dflags     = dd->dd_Flags;
		ef->dviewmodes = dd->dd_ViewModes;
	}

	IIcon->IconControl(icon, ICONCTRLA_GetImageDataFormat, &fmt, TAG_DONE);
	if (fmt == IDFMT_DIRECTMAPPED || fmt == IDFMT_PALETTEMAPPED)
	{
		IIcon->IconControl(icon,
			ICONCTRLA_GetWidth,      &w,
			ICONCTRLA_GetHeight,     &h,
			ICONCTRLA_GetImageData1, &d1,
			ICONCTRLA_GetImageData2, &d2,
			ICONCTRLA_HasRealImage2, &real2,
			TAG_DONE);
		for (i = 0; i < 2; i++)
		{
			EFImage *img = &ef->img[i];
			uint8 *d = i ? d2 : d1;
			if (!d || (i && !real2)) continue;
			img->present = 1;
			img->kind    = fmt == IDFMT_DIRECTMAPPED ? EF_ARGB : EF_CLUT;
			img->width   = w;
			img->height  = h;
			img->data    = d;
			if (img->kind == EF_CLUT)
			{
				struct ColorRegister *pal = NULL;
				uint32 palsize = 0;
				int32 trans = -1;
				IIcon->IconControl(icon,
					i ? ICONCTRLA_GetPalette2 : ICONCTRLA_GetPalette1, &pal,
					i ? ICONCTRLA_GetPaletteSize2 : ICONCTRLA_GetPaletteSize1, &palsize,
					i ? ICONCTRLA_GetTransparentColor2 : ICONCTRLA_GetTransparentColor1, &trans,
					TAG_DONE);
				if (!pal || palsize < 1 || palsize > 256) { img->present = 0; continue; }
				img->palette     = (const uint8_t *)pal;
				img->palsize     = palsize;
				img->transparent = (trans >= 0 && trans < (int32)palsize) ? trans : -1;
			}
			img->datalen = ef_image_datalen(img);
			if (!img->datalen) img->present = 0;
		}
		if (!ef->img[0].present) ef->img[1].present = 0;
	}
	md = our_data(eb, icon);
	if (md && md->composed)
	{
		/* Still the composed picture? Then write the icon's own images from the file.
		 * Otherwise a program gave the icon new images: they become its own (the
		 * planar fallback is made at load time); when it changed only one of them,
		 * the other stays the file's own (keep_own()). */
		BOOL size = fmt == IDFMT_DIRECTMAPPED && w == md->cw && h == md->ch;
		BOOL same1 = size && d1 && fingerprint(d1, w * h * 4) == md->crc1;
		BOOL same2 = md->has2 ? size && d2 && real2 && fingerprint(d2, w * h * 4) == md->crc2
		                      : !ef->img[1].present;
		if (same1 && same2)
		{
			ef->img[0].present = ef->img[1].present = 0;
			ef->gwidth  = md->gwidth;
			ef->gheight = md->gheight;
			ef->gflags  = md->gflags;
			if (md->planarlen && !(dropplanar && md->chunky))
			{
				ef->unknown[ef->nunknown].data = md->data;
				ef->unknown[ef->nunknown].len  = md->planarlen;
				ef->nunknown++;
			}
			if (md->chunkylen)
			{
				ef->unknown[ef->nunknown].data = md->data + md->planarlen;
				ef->unknown[ef->nunknown].len  = md->chunkylen;
				ef->nunknown++;
			}
		}
		else if (!(same1 || same2) || !keep_own(eb, md, ef, sb, same1 ? 0 : 1))
		{
			ef->gwidth  = w;
			ef->gheight = h;
		}
	}
	else if (ef->img[0].present && md && md->chunky)
	{
		/* chunky icon we loaded: write back the file's own planar fallback (none = we
		 * make one at load time) and gadget size, not what layout left in GadgetRender */
		ef->gwidth  = md->gwidth;
		ef->gheight = md->gheight;
		if (md->planarlen && !dropplanar)
		{
			ef->unknown[ef->nunknown].data = md->data;
			ef->unknown[ef->nunknown].len  = md->planarlen;
			ef->nunknown++;
		}
	}
	else if ((icon->do_Gadget.Flags & GFLG_GADGIMAGE) && !(dropplanar && ef->img[0].present))
	{
		/* planar images: the only ones of old icons, the fallback of chunky ones */
		get_planar(icon->do_Gadget.GadgetRender, &ef->planar[0]);
		if (ef->planar[0].present && (icon->do_Gadget.Flags & GFLG_GADGHIGHBITS) == GFLG_GADGHIMAGE)
			get_planar(icon->do_Gadget.SelectRender, &ef->planar[1]);
		/* Note: if a program lays out a native chunky icon and then converts it, this is the
		 * screen-remapped copy (EmblemIcon loads without remapping). Native files can hold
		 * genuine 8-plane fallbacks (SYS:Disk.info), so the two can't be told apart here. */
	}

	if (md && md->unknownlen)
	{
		/* stored as one block of whole chunks */
		ef->unknown[ef->nunknown].data = md->data + md->planarlen + md->chunkylen;
		ef->unknown[ef->nunknown].len  = md->unknownlen;
		ef->nunknown++;
	}

	if (setsettings)
	{
		if (!pack_strings((STRPTR *)setsettings->ti_Data, &sb->settings, &ef->settingslen))
			return ERROR_NO_FREE_STORE;
		ef->settings = sb->settings;
	}
	else if (md && md->settingslen)
	{
		ef->settings    = (const char *)md->data + md->planarlen + md->chunkylen + md->unknownlen;
		ef->settingslen = md->settingslen;
	}
	return 0;
}

static BOOL update_position(CONST_STRPTR name, struct DiskObject *icon)
{
	uint8 head[24], pos[8];
	BOOL ok = FALSE;
	BPTR fh = IDOS->Open(name, MODE_OLDFILE);
	if (!fh) return FALSE;
	if (IDOS->Read(fh, head, sizeof(head)) == (int32)sizeof(head) && ef_is_emblem(head, sizeof(head)))
	{
		uint32 x = (uint32)icon->do_CurrentX, y = (uint32)icon->do_CurrentY;
		pos[0] = x >> 24; pos[1] = x >> 16; pos[2] = x >> 8; pos[3] = x;
		pos[4] = y >> 24; pos[5] = y >> 16; pos[6] = y >> 8; pos[7] = y;
		if (IDOS->ChangeFilePosition(fh, EF_POSOFFSET, OFFSET_BEGINNING)
			&& IDOS->Write(fh, pos, sizeof(pos)) == (int32)sizeof(pos))
			ok = TRUE;
	}
	IDOS->Close(fh);
	return ok;
}

/* ---- main interface ---- */

static uint32 APICALL m_Obtain(struct IconModuleIFace *Self) { return ++Self->Data.RefCount; }
static uint32 APICALL m_Release(struct IconModuleIFace *Self) { return --Self->Data.RefCount; }

static uint32 APICALL m_ModuleControlA(struct IconModuleIFace *Self, APTR object, struct TagItem *tags)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	struct TagItem *state = tags, *ti, **errtag;
	uint32 n = 0;
	int32 err = 0;

	errtag = (struct TagItem **)IUtility->GetTagData(IMA_ErrorTagItem, 0, tags);
	if (errtag) *errtag = NULL;
	while ((ti = IUtility->NextTagItem(&state)))
	{
		switch (ti->ti_Tag)
		{
			case IMA_ErrorCode:
			case IMA_ErrorTagItem:
			case IMA_FreeList:
				break;
			case IMA_GetFormatNames:      *(CONST_STRPTR **)ti->ti_Data = FormatNames; break;
			case IMA_GetFormatDescs:      *(CONST_STRPTR **)ti->ti_Data = FormatDescs; break;
			case IMA_SetIconBase:         IconBase = (struct Library *)ti->ti_Data; break;
			case IMA_SetIconIFace:        IIcon = (struct IconIFace *)ti->ti_Data; break;
			case IMA_SetMaxUnknownDataSize: eb->maxunknown = ti->ti_Data; break;
			case IMA_GetLoadSupport:      *(uint32 *)ti->ti_Data = TRUE; break;
			case IMA_GetSaveSupport:      *(uint32 *)ti->ti_Data = TRUE; break;
			case IMA_GetScaleSupport:     *(uint32 *)ti->ti_Data = FALSE; break;
			case IMA_GetConvertSupport:   *(uint32 *)ti->ti_Data = TRUE; break;
			case IMA_GetFileFormat:
				if (object && IIcon && our_data(eb, object))
					*(CONST_STRPTR *)ti->ti_Data = FORMAT;
				else
					err = ERROR_OBJECT_WRONG_TYPE;
				break;
			default:
				err = ERROR_NOT_IMPLEMENTED;
				break;
		}
		if (err)
		{
			if (errtag) *errtag = ti;
			break;
		}
		n++;
	}
	set_error(tags, err);
	return n;
}

static uint32 VARARGS68K m_ModuleControl(struct IconModuleIFace *Self, APTR object, ...)
{
	va_list ap;
	uint32 r;
	va_startlinear(ap, object);
	r = Self->ModuleControlA(object, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static struct DiskObject * APICALL m_LoadIconA(struct IconModuleIFace *Self, CONST_STRPTR name,
	struct DiskObject *icon, struct TagItem *tags)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	struct FreeList *fl = (struct FreeList *)IUtility->GetTagData(IMA_FreeList, 0, tags);
	CONST_STRPTR *fmtp = (CONST_STRPTR *)IUtility->GetTagData(IMA_LoadFormat, 0, tags);
	uint8 *buf;
	uint32 len = 0;
	int32 err;
	EFIcon ef;
	int r;

	if (!IIcon || !name)
	{
		set_error(tags, ERROR_OBJECT_WRONG_TYPE);
		return NULL;
	}
	if (!icon)
	{
		/* identify only */
		uint8 head[24];
		BPTR fh = IDOS->Open(name, MODE_OLDFILE);
		err = ERROR_OBJECT_WRONG_TYPE;
		if (fh)
		{
			if (IDOS->Read(fh, head, sizeof(head)) == (int32)sizeof(head) && ef_is_emblem(head, sizeof(head)))
				err = 0;
			IDOS->Close(fh);
		}
		else
			err = IDOS->IoErr();
		if (!err && fmtp) *fmtp = FORMAT;
		set_error(tags, err);
		return NULL;
	}

	PROF_START(tall);
	PROF_START(tr);
	if (!(buf = read_file(name, &len, &err)))
	{
		set_error(tags, err);
		return NULL;
	}
	PROF_ADD(0, tr);
	PROF_START(tq);
	r = ef_parse(buf, len, &ef);
	PROF_ADD(1, tq);
	PROF_START(tf);
	if (r != EF_OK)
		err = ef_to_doserr(r);
	else if (!fl)
		err = ERROR_REQUIRED_ARG_MISSING;
	else
	{
		struct TagItem *origtags = (struct TagItem *)IUtility->GetTagData(IMA_TagList, 0, tags);
		err = fill_icon(eb, icon, fl, &ef,
			origtags && IUtility->GetTagData(EMBLEMA_NoCompose, FALSE, origtags),
			origtags ? (STRPTR **)IUtility->GetTagData(EMBLEMA_GetSettings, 0, origtags) : NULL);
	}
	PROF_ADD(2, tf);
	IExec->FreeVec(buf);
	PROF_ADD(11, tall);
#ifdef EMBLEM_PROFILE
	if (ITimer && ++profn % 200 == 0)
	{
		int k;
		IExec->DebugPrintF("[emblem profile] %lu loads, average us:", profn);
		for (k = 0; k < 12; k++) IExec->DebugPrintF(" %s=%lu", profname[k], (uint32)(prof[k] / 200));
		IExec->DebugPrintF("\n");
		for (k = 0; k < 12; k++) prof[k] = 0;
	}
#endif

	set_error(tags, err);
	if (err) return NULL;
	if (fmtp) *fmtp = FORMAT;
	return icon;
}

static struct DiskObject * VARARGS68K m_LoadIcon(struct IconModuleIFace *Self, CONST_STRPTR name,
	struct DiskObject *icon, ...)
{
	va_list ap;
	struct DiskObject *r;
	va_startlinear(ap, icon);
	r = Self->LoadIconA(name, icon, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static uint32 APICALL m_SaveIconA(struct IconModuleIFace *Self, CONST_STRPTR name,
	struct DiskObject *icon, struct TagItem *tags)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	CONST_STRPTR fmt = (CONST_STRPTR)IUtility->GetTagData(IMA_SaveFormat, 0, tags);
	struct TagItem *origtags = (struct TagItem *)IUtility->GetTagData(IMA_TagList, 0, tags);
	struct SaveBuf sb = { NULL, NULL, NULL };
	uint8 *buf = NULL;
	uint32_t bound, len = 0;
	int32 err = 0;
	EFIcon ef;
	BPTR fh;

	if (!IIcon || !name || !icon)
	{
		set_error(tags, ERROR_REQUIRED_ARG_MISSING);
		return FALSE;
	}
	if (fmt && IUtility->Stricmp(fmt, FORMAT) != 0)
	{
		set_error(tags, ERROR_ACTION_NOT_KNOWN);
		return FALSE;
	}
	if (origtags && IUtility->GetTagData(ICONPUTA_OnlyUpdatePosition, FALSE, origtags)
		&& update_position(name, icon))
	{
		set_error(tags, 0);
		return TRUE;
	}

	if (!(err = icon_to_ef(eb, icon, &ef, &sb,
		origtags ? IUtility->FindTagItem(EMBLEMA_SetSettings, origtags) : NULL,
		origtags && IUtility->GetTagData(ICONPUTA_DropPlanarIconImage, FALSE, origtags))))
	{
		bound = ef_write_bound(&ef);
		if (!(buf = IExec->AllocVecTags(bound, AVT_Type, MEMF_PRIVATE, TAG_DONE)))
			err = ERROR_NO_FREE_STORE;
		else
		{
			int r = ef_write(&ef, buf, bound, &len, z_compress, get_z(eb));
			if (r != EF_OK) err = ef_to_doserr(r);
		}
	}
	if (!err)
	{
		if (!(fh = IDOS->Open(name, MODE_NEWFILE)))
			err = IDOS->IoErr();
		else
		{
			if (IDOS->Write(fh, buf, len) != (int32)len)
				err = IDOS->IoErr() ? IDOS->IoErr() : ERROR_DISK_FULL;
			if (!IDOS->Close(fh) && !err)
				err = IDOS->IoErr();
			if (err)
				IDOS->Delete(name);   /* a half-written icon is worse than none */
		}
	}
	if (buf) IExec->FreeVec(buf);
	if (sb.tooltypes) IExec->FreeVec(sb.tooltypes);
	if (sb.settings) IExec->FreeVec(sb.settings);
	if (sb.own) IExec->FreeVec(sb.own);
	set_error(tags, err);
	return err ? FALSE : TRUE;
}

static uint32 VARARGS68K m_SaveIcon(struct IconModuleIFace *Self, CONST_STRPTR name, struct DiskObject *icon, ...)
{
	va_list ap;
	uint32 r;
	va_startlinear(ap, icon);
	r = Self->SaveIconA(name, icon, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static uint32 APICALL m_AllocIconDataA(struct IconModuleIFace *Self, struct DiskObject *icon, struct TagItem *tags)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	struct FreeList *fl = (struct FreeList *)IUtility->GetTagData(IMA_FreeList, 0, tags);
	struct EmblemData *md;

	if (!IIcon || !icon || !fl)
	{
		set_error(tags, ERROR_REQUIRED_ARG_MISSING);
		return FALSE;
	}
	if (!(md = IIcon->FreeAlloc(fl, sizeof(*md), MEMF_SHARED | MEMF_CLEAR)))
	{
		set_error(tags, ERROR_NO_FREE_STORE);
		return FALSE;
	}
	md->owner = &eb->lib;
	IIcon->IconControl(icon, ICONCTRLA_SetIconModuleData, md, TAG_DONE);
	set_error(tags, 0);
	return TRUE;
}

static uint32 VARARGS68K m_AllocIconData(struct IconModuleIFace *Self, struct DiskObject *icon, ...)
{
	va_list ap;
	uint32 r;
	va_startlinear(ap, icon);
	r = Self->AllocIconDataA(icon, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static void APICALL m_FreeIconDataA(struct IconModuleIFace *Self, struct DiskObject *icon, struct TagItem *tags)
{
	/* everything is on the icon's FreeList */
}

static void VARARGS68K m_FreeIconData(struct IconModuleIFace *Self, struct DiskObject *icon, ...)
{
	va_list ap;
	va_startlinear(ap, icon);
	Self->FreeIconDataA(icon, LINEARTAGS(ap));
	va_end(ap);
}

static APTR APICALL m_DupIconDataA(struct IconModuleIFace *Self, struct DiskObject *icon, struct TagItem *tags)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	struct FreeList *fl = (struct FreeList *)IUtility->GetTagData(IMA_FreeList, 0, tags);
	struct EmblemData *md, *copy;
	uint32 size;

	if (!IIcon || !(md = our_data(eb, icon)))
	{
		set_error(tags, icon ? ERROR_OBJECT_WRONG_TYPE : 0);
		return NULL;
	}
	size = sizeof(*md) + md->planarlen + md->chunkylen + md->unknownlen + md->settingslen;
	if (!fl || !(copy = IIcon->FreeAlloc(fl, size, MEMF_SHARED)))
	{
		set_error(tags, ERROR_NO_FREE_STORE);
		return NULL;
	}
	IExec->CopyMem(md, copy, size);
	set_error(tags, 0);
	return copy;
}

static APTR VARARGS68K m_DupIconData(struct IconModuleIFace *Self, struct DiskObject *icon, ...)
{
	va_list ap;
	APTR r;
	va_startlinear(ap, icon);
	r = Self->DupIconDataA(icon, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static uint32 APICALL m_ScaleIconA(struct IconModuleIFace *Self, struct DiskObject *icon,
	struct IconScaleRequest *isr, struct TagItem *tags)
{
	set_error(tags, ERROR_NOT_IMPLEMENTED);
	return FALSE;
}

static uint32 VARARGS68K m_ScaleIcon(struct IconModuleIFace *Self, struct DiskObject *icon,
	struct IconScaleRequest *isr, ...)
{
	va_list ap;
	uint32 r;
	va_startlinear(ap, isr);
	r = Self->ScaleIconA(icon, isr, LINEARTAGS(ap));
	va_end(ap);
	return r;
}

static const APTR main_vectors[] =
{
	(APTR)m_Obtain, (APTR)m_Release, NULL, NULL,
	(APTR)m_ModuleControlA, (APTR)m_ModuleControl,
	(APTR)m_LoadIconA,      (APTR)m_LoadIcon,
	(APTR)m_SaveIconA,      (APTR)m_SaveIcon,
	(APTR)m_AllocIconDataA, (APTR)m_AllocIconData,
	(APTR)m_FreeIconDataA,  (APTR)m_FreeIconData,
	(APTR)m_DupIconDataA,   (APTR)m_DupIconData,
	(APTR)m_ScaleIconA,     (APTR)m_ScaleIcon,
	(APTR)-1
};

/* ---- library manager ---- */

static uint32 APICALL lm_Obtain(struct LibraryManagerInterface *Self) { return ++Self->Data.RefCount; }
static uint32 APICALL lm_Release(struct LibraryManagerInterface *Self) { return --Self->Data.RefCount; }

static void close_libs(struct EmblemBase *eb)
{
	if (eb->IZ) IExec->DropInterface((struct Interface *)eb->IZ);
	if (eb->ZBase) IExec->CloseLibrary(eb->ZBase);
	eb->IZ = NULL;
	eb->ZBase = NULL;
	if (IUtility) IExec->DropInterface((struct Interface *)IUtility);
	if (UtilityBase) IExec->CloseLibrary(UtilityBase);
	if (IDOS) IExec->DropInterface((struct Interface *)IDOS);
	if (DOSBase) IExec->CloseLibrary(DOSBase);
	IUtility = NULL; UtilityBase = NULL; IDOS = NULL; DOSBase = NULL;
}

static BPTR APICALL lm_Expunge(struct LibraryManagerInterface *Self)
{
	struct EmblemBase *eb = (struct EmblemBase *)Self->Data.LibBase;
	BPTR seg = 0;
	if (eb->lib.lib_OpenCnt == 0)
	{
		seg = eb->seglist;
		IExec->Remove(&eb->lib.lib_Node);
		ic_cleanup();
		close_libs(eb);
		IExec->DeleteLibrary(&eb->lib);
	}
	else
		eb->lib.lib_Flags |= LIBF_DELEXP;
	return seg;
}

static struct Library * APICALL lm_Open(struct LibraryManagerInterface *Self, uint32 version)
{
	struct Library *lib = Self->Data.LibBase;
	lib->lib_OpenCnt++;
	lib->lib_Flags &= ~LIBF_DELEXP;
	return lib;
}

static BPTR APICALL lm_Close(struct LibraryManagerInterface *Self)
{
	struct Library *lib = Self->Data.LibBase;
	lib->lib_OpenCnt--;
	if (lib->lib_OpenCnt == 0 && (lib->lib_Flags & LIBF_DELEXP))
		return lm_Expunge(Self);
	return 0;
}

static const APTR lib_manager_vectors[] =
{
	(APTR)lm_Obtain, (APTR)lm_Release, NULL, NULL,
	(APTR)lm_Open, (APTR)lm_Close, (APTR)lm_Expunge, NULL,
	(APTR)-1
};

static const struct TagItem lib_managerTags[] =
{
	{ MIT_Name,        (Tag)"__library" },
	{ MIT_VectorTable, (Tag)lib_manager_vectors },
	{ MIT_Version,     1 },
	{ TAG_DONE,        0 }
};

static const struct TagItem main_Tags[] =
{
	{ MIT_Name,        (Tag)"main" },
	{ MIT_VectorTable, (Tag)main_vectors },
	{ MIT_Version,     1 },
	{ TAG_DONE,        0 }
};

static const CONST_APTR libInterfaces[] = { lib_managerTags, main_Tags, NULL };

static struct Library *libInit(struct Library *lib, BPTR seglist, struct ExecIFace *iexec)
{
	struct EmblemBase *eb = (struct EmblemBase *)lib;

	IExec = iexec;
	lib->lib_Node.ln_Type = NT_LIBRARY;
	lib->lib_Node.ln_Pri  = 0;
	lib->lib_Node.ln_Name = (STRPTR)LIBNAME;
	lib->lib_Flags        = LIBF_SUMUSED | LIBF_CHANGED;
	lib->lib_Version      = VERSION;
	lib->lib_Revision     = REVISION;
	lib->lib_IdString     = (STRPTR)VSTRING;
	eb->seglist    = seglist;
	eb->maxunknown = 128;
	IExec->InitSemaphore(&eb->zsem);
	ic_init();

#ifdef EMBLEM_PROFILE
	{
		struct ExecBase *sysbase = (struct ExecBase *)IExec->Data.LibBase;
		struct Library *tb;
		IExec->Forbid();
		tb = (struct Library *)IExec->FindName(&sysbase->DeviceList, TIMERNAME);
		IExec->Permit();
		if (tb) ITimer = (struct TimerIFace *)IExec->GetInterface(tb, "main", 1, NULL);
		IExec->DebugPrintF("[emblem profile] timer %p\n", ITimer);
	}
#endif
	DOSBase = IExec->OpenLibrary("dos.library", 53);
	IDOS = DOSBase ? (struct DOSIFace *)IExec->GetInterface(DOSBase, "main", 1, NULL) : NULL;
	UtilityBase = IExec->OpenLibrary("utility.library", 53);
	IUtility = UtilityBase ? (struct UtilityIFace *)IExec->GetInterface(UtilityBase, "main", 1, NULL) : NULL;
	if (!IDOS || !IUtility)
	{
		close_libs(eb);
		return NULL;
	}
	return lib;
}

static const struct TagItem libCreateTags[] =
{
	{ CLT_DataSize,   sizeof(struct EmblemBase) },
	{ CLT_InitFunc,   (Tag)libInit },
	{ CLT_Interfaces, (Tag)libInterfaces },
	{ TAG_DONE,       0 }
};

static const struct Resident lib_res __attribute__((used)) =
{
	RTC_MATCHWORD,
	(struct Resident *)&lib_res,
	(APTR)(&lib_res + 1),
	RTF_NATIVE | RTF_AUTOINIT,
	VERSION,
	NT_LIBRARY,
	0,
	(STRPTR)LIBNAME,
	(STRPTR)VSTRING,
	(APTR)libCreateTags
};
