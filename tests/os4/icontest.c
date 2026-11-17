/*
 * icontest - guest helper for the Emblem module tests (not shipped).
 *
 *   icontest dump NAME          canonical dump of everything icon.library returns
 *   icontest make KIND NAME     write a native test icon: argb, argb1, clut, clut1, planar, drawer
 *   icontest tt NAME STRING     add a tool type and save (what the Information window does);
 *                               IMAGE=, IMAGESELECTED=, EMBLEM=, EMBLEMSELECTED= are added to
 *                               the Emblem settings instead (EMBLEMA_SetSettings)
 *   icontest ttonly NAME STRING the same, always as a tool type (how Emblem 1.0 kept the settings)
 *   icontest pos NAME X Y       snapshot: ICONPUTA_OnlyUpdatePosition
 *   icontest dup NAME NEW       DupDiskObject() and save under a new name
 *   icontest layoutsave NAME N  load on the Workbench screen, lay out, set stack N, save
 *   icontest setimg NAME        give the icon new 20x20 ARGB images and save (an icon editor)
 *   icontest bench NAME N       load and free the icon N times, print the time
 *   icontest pixels NAME PREFIX write the chunky images as PREFIX_1.argb / PREFIX_2.argb
 *                               (palette and planar images converted like the module does)
 *   icontest ttfile NAME FILE   replace the tool types (and the settings, sorted out like tt)
 *                               with the lines of FILE and save
 *   icontest loadall DIR [N]    load + lay out (Workbench screen) every icon in DIR, N rounds, timed
 *   icontest leak NAME N        free memory before/after N loads (after a warm-up)
 *   icontest screen DEPTH SECS [SAVE] NAME...
 *                               open a screen of DEPTH bits, lay out and draw the icons (normal,
 *                               selected), keep it SECS seconds, with SAVE write the icons back
 *   icontest raw CMD ...        the same, with EMBLEMA_NoCompose (the icon's own images)
 *
 * NAME without ".info". Output lines are "key=value" so the host can diff dumps;
 * dump prints the tool types as tt= lines, the Emblem settings as es= lines.
 */
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/icon.h>
#include <proto/utility.h>
#include <workbench/icon.h>
#include <intuition/intuition.h>
#include <proto/intuition.h>
#include <proto/graphics.h>
#include <graphics/gfx.h>
#include <string.h>
#include "../../src/emblem.h"
#include "../../src/compose.h"
#include <stdlib.h>
#include <stdio.h>

static uint32 crc32(const uint8 *p, uint32 n)
{
	uint32 c = 0xFFFFFFFF;
	while (n--)
	{
		c ^= *p++;
		for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320 & -(c & 1));
	}
	return ~c;
}

static BOOL raw = FALSE;   /* load with EMBLEMA_NoCompose: the icon's own images */
static STRPTR *settings;   /* EMBLEMA_GetSettings of the last load() */

/* the keys kept in the Emblem file instead of the tool types */
static BOOL is_setting(CONST_STRPTR s)
{
	static const char *const keys[] = { "IMAGE", "IMAGESELECTED", "EMBLEM", "EMBLEMSELECTED" };
	const char *e = strchr(s, '=');
	size_t n = e ? (size_t)(e - s) : strlen(s);
	for (int i = 0; i < 4; i++)
		if (n == strlen(keys[i]) && Strnicmp(s, keys[i], n) == 0) return TRUE;
	return FALSE;
}

static struct DiskObject *load(CONST_STRPTR name, STRPTR *fmt)
{
	int32 err = 0;
	settings = NULL;
	struct DiskObject *d = GetIconTags(name,
		ICONGETA_FailIfUnavailable, TRUE,
		ICONGETA_RemapIcon,         FALSE,
		ICONGETA_GenerateImageMasks, FALSE,
		ICONGETA_FileFormat,        fmt,
		ICONA_ErrorCode,            &err,
		EMBLEMA_NoCompose,          raw,
		EMBLEMA_GetSettings,        &settings,
		TAG_DONE);
	if (!d) Printf("error=load %ld\n", err);
	return d;
}

static void dump_planar(CONST_STRPTR key, int n, const struct Image *im)
{
	if (!im) { Printf("%s%ld=none\n", key, n); return; }
	uint32 len = im->ImageData ? im->Depth * im->Height * ((im->Width + 15) / 16) * 2 : 0;
	Printf("%s%ld=%ld,%ld,%ld,%ld,%ld,%ld,%ld,%08lx\n", key, n, im->LeftEdge, im->TopEdge, im->Width,
		im->Height, im->Depth, im->PlanePick, im->PlaneOnOff, len ? crc32((uint8 *)im->ImageData, len) : 0);
}

static int dump(CONST_STRPTR name)
{
	STRPTR fmt = NULL;
	struct DiskObject *d = load(name, &fmt);
	if (!d) return 10;
	Printf("format=%s\n", fmt ? fmt : (STRPTR)"?");
	Printf("type=%ld\n", d->do_Type);
	Printf("deftool=%s\n", d->do_DefaultTool ? d->do_DefaultTool : (STRPTR)"(none)");
	for (STRPTR *tt = d->do_ToolTypes; tt && *tt; tt++) Printf("tt=%s\n", *tt);
	for (STRPTR *es = settings; es && *es; es++) Printf("es=%s\n", *es);
	Printf("pos=%ld,%ld\n", d->do_CurrentX, d->do_CurrentY);
	Printf("stack=%ld\n", d->do_StackSize);
	Printf("toolwindow=%s\n", d->do_ToolWindow ? d->do_ToolWindow : (STRPTR)"(none)");
	if (d->do_DrawerData)
	{
		struct DrawerData *dd = d->do_DrawerData;
		Printf("drawer=%ld,%ld,%ld,%ld,%ld,%ld,%08lx,%ld\n", dd->dd_NewWindow.LeftEdge, dd->dd_NewWindow.TopEdge,
			dd->dd_NewWindow.Width, dd->dd_NewWindow.Height, dd->dd_CurrentX, dd->dd_CurrentY,
			dd->dd_Flags, dd->dd_ViewModes);
	}
	else
		Printf("drawer=none\n");

	uint32 f = 0, w = 0, h = 0, frameless = 0;
	int32 real2 = 0;
	uint8 aspect = 0;
	IconControl(d, ICONCTRLA_GetImageDataFormat, &f, ICONCTRLA_GetFrameless, &frameless,
		ICONCTRLA_GetAspectRatio, &aspect, TAG_DONE);
	Printf("frameless=%ld\naspect=%ld\n", frameless, aspect);
	Printf("gadget=%04lx,%ld,%ld\n", d->do_Gadget.Flags, d->do_Gadget.Width, d->do_Gadget.Height);
	Printf("imgfmt=%ld\n", f);
	if (f == IDFMT_DIRECTMAPPED || f == IDFMT_PALETTEMAPPED)
	{
		BOOL sel = (d->do_Gadget.Flags & GFLG_GADGHIGHBITS) == GFLG_GADGHIMAGE;
		dump_planar("fallback", 1, (d->do_Gadget.Flags & GFLG_GADGIMAGE) ? d->do_Gadget.GadgetRender : NULL);
		dump_planar("fallback", 2, (d->do_Gadget.Flags & GFLG_GADGIMAGE) && sel ? d->do_Gadget.SelectRender : NULL);
		uint8 *d1 = NULL, *d2 = NULL;
		IconControl(d, ICONCTRLA_GetWidth, &w, ICONCTRLA_GetHeight, &h, ICONCTRLA_GetImageData1, &d1,
			ICONCTRLA_GetImageData2, &d2, ICONCTRLA_HasRealImage2, &real2, TAG_DONE);
		uint32 bpp = f == IDFMT_DIRECTMAPPED ? 4 : 1;
		Printf("size=%ldx%ld\nreal2=%ld\n", w, h, real2 ? 1 : 0);
		Printf("img1=%08lx\n", d1 ? crc32(d1, w * h * bpp) : 0);
		if (real2) Printf("img2=%08lx\n", d2 ? crc32(d2, w * h * bpp) : 0);
		if (f == IDFMT_PALETTEMAPPED)
		{
			for (int i = 0; i < (real2 ? 2 : 1); i++)
			{
				struct ColorRegister *pal = NULL;
				uint32 ps = 0;
				int32 tr = -1;
				IconControl(d, i ? ICONCTRLA_GetPalette2 : ICONCTRLA_GetPalette1, &pal,
					i ? ICONCTRLA_GetPaletteSize2 : ICONCTRLA_GetPaletteSize1, &ps,
					i ? ICONCTRLA_GetTransparentColor2 : ICONCTRLA_GetTransparentColor1, &tr, TAG_DONE);
				Printf("pal%ld=%ld,%ld,%08lx\n", i + 1, ps, tr, pal ? crc32((uint8 *)pal, ps * 3) : 0);
			}
		}
	}
	else
	{
		dump_planar("planar", 1, d->do_Gadget.GadgetRender);
		dump_planar("planar", 2, (d->do_Gadget.Flags & GFLG_GADGHIGHBITS) == GFLG_GADGHIMAGE ? d->do_Gadget.SelectRender : NULL);
	}
	FreeDiskObject(d);
	return 0;
}

static STRPTR TT[] = { (STRPTR)"(EMBLEM=EmblemTest,0,0,4,4,SHADOW)", (STRPTR)"DONOTWAIT", (STRPTR)"(TEST=1)", NULL };
static UWORD planar1[2 * 20 * 2], planar2[2 * 20 * 2];
static struct Image pimg1 = { 0, 0, 32, 20, 2, planar1, 3, 0, NULL };
static struct Image pimg2 = { 0, 0, 32, 20, 2, planar2, 3, 0, NULL };

static int make(CONST_STRPTR kind, CONST_STRPTR name)
{
	BOOL drawer = Stricmp(kind, "drawer") == 0;
	BOOL planar = Stricmp(kind, "planar") == 0;
	BOOL clut = Strnicmp(kind, "clut", 4) == 0;
	BOOL second = !(Stricmp(kind, "argb1") == 0 || Stricmp(kind, "clut1") == 0 || drawer);
	int32 dtype = drawer ? WBDRAWER : clut ? WBPROJECT : WBTOOL;
	/* GetDefDiskObject: a complete icon (NewDiskObject ones can't be saved natively once chunky) */
	struct DiskObject *d = planar ? NewDiskObject(dtype) : GetDefDiskObject(dtype);
	uint32 *a1 = NULL, *a2 = NULL;
	if (!d) { Printf("error=newdiskobject\n"); return 10; }
	STRPTR *oldtt = d->do_ToolTypes, olddt = d->do_DefaultTool, oldtw = d->do_ToolWindow;

	d->do_ToolTypes = TT;
	d->do_CurrentX = 20;
	d->do_CurrentY = 30;
	d->do_StackSize = drawer ? 0 : 65536;
	if (!drawer) d->do_ToolWindow = (STRPTR)"CON:0/0/400/100/Test";
	if (clut) d->do_DefaultTool = (STRPTR)"SYS:Utilities/MultiView";
	if (drawer && d->do_DrawerData)
	{
		d->do_DrawerData->dd_NewWindow.LeftEdge = 50;
		d->do_DrawerData->dd_NewWindow.TopEdge = 60;
		d->do_DrawerData->dd_NewWindow.Width = 400;
		d->do_DrawerData->dd_NewWindow.Height = 300;
		d->do_DrawerData->dd_CurrentX = 5;
		d->do_DrawerData->dd_CurrentY = 7;
		d->do_DrawerData->dd_Flags = DDFLAGS_SHOWALL;
		d->do_DrawerData->dd_ViewModes = DDVM_BYNAME;
	}

	if (planar)
	{
		for (int i = 0; i < 2 * 20 * 2; i++) { planar1[i] = 0x0F0F ^ (i * 0x1111); planar2[i] = ~planar1[i]; }
		IconControl(d, ICONCTRLA_SetImageDataFormat, IDFMT_BITMAPPED, TAG_DONE);
		d->do_Gadget.GadgetRender = &pimg1;
		d->do_Gadget.SelectRender = &pimg2;
		d->do_Gadget.Flags = GFLG_GADGIMAGE | GFLG_GADGHIMAGE;
		d->do_Gadget.Width = 32;
		d->do_Gadget.Height = 21;
	}
	else if (clut)
	{
		static UBYTE px1[40 * 30], px2[40 * 30];
		static struct ColorRegister pal1[16], pal2[16];
		for (int i = 0; i < 16; i++)
		{
			pal1[i].red = i * 16; pal1[i].green = 255 - i * 16; pal1[i].blue = 128;
			pal2[i].red = 255 - i * 8; pal2[i].green = i * 8; pal2[i].blue = 64;
		}
		for (int i = 0; i < 40 * 30; i++) { px1[i] = (i / 3) % 16; px2[i] = (i / 5) % 16; }
		IconControl(d, ICONCTRLA_SetImageDataFormat, IDFMT_PALETTEMAPPED,
			ICONCTRLA_SetWidth, 40, ICONCTRLA_SetHeight, 30,
			ICONCTRLA_SetPaletteSize1, 16, ICONCTRLA_SetPalette1, pal1,
			ICONCTRLA_SetTransparentColor1, 0, ICONCTRLA_SetImageData1, px1, TAG_DONE);
		if (second)
			IconControl(d, ICONCTRLA_SetPaletteSize2, 16, ICONCTRLA_SetPalette2, pal2,
				ICONCTRLA_SetTransparentColor2, -1, ICONCTRLA_SetImageData2, px2, TAG_DONE);
	}
	else
	{
		uint32 w = drawer ? 56 : 48, h = drawer ? 48 : 40;
		a1 = AllocVecTags(w * h * 4, TAG_DONE);
		a2 = AllocVecTags(w * h * 4, TAG_DONE);
		for (uint32 y = 0; y < h; y++)
			for (uint32 x = 0; x < w; x++)
			{
				uint32 alpha = (x < 2 || y < 2 || x >= w - 2 || y >= h - 2) ? 0 : 0xFF;
				a1[y * w + x] = (alpha << 24) | ((x * 255 / w) << 16) | ((y * 255 / h) << 8) | 0x40;
				a2[y * w + x] = (alpha << 24) | ((255 - x * 255 / w) << 16) | 0x2000 | (y * 255 / h);
			}
		IconControl(d, ICONCTRLA_SetImageDataFormat, IDFMT_DIRECTMAPPED,
			ICONCTRLA_SetWidth, w, ICONCTRLA_SetHeight, h, ICONCTRLA_SetImageData1, a1, TAG_DONE);
		if (second) IconControl(d, ICONCTRLA_SetImageData2, a2, TAG_DONE);
	}

	/* ask for the native format three ways; report which one icon.library takes */
	int32 err = 0;
	BOOL ok = PutIconTags(name, d, ICONPUTA_FileFormat, ~0UL, ICONA_ErrorCode, &err, TAG_DONE);
	if (!ok)
	{
		Printf("note=~0 failed %ld\n", err);
		err = 0;
		ok = PutIconTags(name, d, ICONPUTA_FileFormat, (uint32)"Amiga", ICONA_ErrorCode, &err, TAG_DONE);
		if (!ok) { Printf("note=Amiga failed %ld\n", err); err = 0; ok = PutIconTags(name, d, ICONA_ErrorCode, &err, TAG_DONE); }
	}
	/* don't let FreeDiskObject touch our static data */
	d->do_ToolTypes = oldtt;
	d->do_ToolWindow = oldtw;
	d->do_DefaultTool = olddt;
	if (planar) { d->do_Gadget.GadgetRender = NULL; d->do_Gadget.SelectRender = NULL; }
	FreeDiskObject(d);
	FreeVec(a1);
	FreeVec(a2);
	Printf(ok ? "made=%s\n" : "error=put %ld\n", ok ? (int32)name : err);
	return ok ? 0 : 10;
}

/* es: the settings to save (EMBLEMA_SetSettings), NULL = keep the icon's own */
static int put_es(CONST_STRPTR name, struct DiskObject *d, BOOL onlypos, STRPTR *es)
{
	int32 err = 0;
	BOOL ok = PutIconTags(name, d, ICONPUTA_OnlyUpdatePosition, onlypos, ICONA_ErrorCode, &err,
		es ? EMBLEMA_SetSettings : TAG_IGNORE, (uint32)es, TAG_DONE);
	Printf(ok ? "saved=1\n" : "error=put %ld\n", err);
	return ok ? 0 : 10;
}

static int put(CONST_STRPTR name, struct DiskObject *d, BOOL onlypos) { return put_es(name, d, onlypos, NULL); }

int main(int argc, char **argv)
{
	if (argc >= 2 && !strcmp(argv[1], "raw"))
	{
		raw = TRUE;
		argv++;
		argc--;
	}
	if (argc >= 3 && !strcmp(argv[1], "dump")) return dump(argv[2]);
	if (argc >= 4 && !strcmp(argv[1], "ttfile"))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		BPTR fh;
		int32 len, n = 0, rc;
		char *buf;
		STRPTR *tt, *es, *old;
		int32 nes = 0;
		if (!d) return 10;
		if (!(fh = Open(argv[3], MODE_OLDFILE))) { Printf("error=open\n"); return 10; }
		buf = AllocVecTags(1024 * 1024 + 1, AVT_ClearWithValue, 0, TAG_DONE);
		len = Read(fh, buf, 1024 * 1024);
		Close(fh);
		if (len < 0) len = 0;
		for (int32 i = 0; i < len; i++) if (buf[i] == '\n') n++;
		tt = AllocVecTags((n + 2) * sizeof(STRPTR), AVT_ClearWithValue, 0, TAG_DONE);
		es = AllocVecTags((n + 2) * sizeof(STRPTR), AVT_ClearWithValue, 0, TAG_DONE);
		n = 0;
		for (char *p = buf; p < buf + len; )
		{
			char *e = p;
			while (e < buf + len && *e != '\n') e++;
			*e = 0;
			if (is_setting(p)) es[nes++] = p;
			else tt[n++] = p;
			p = e + 1;
		}
		old = d->do_ToolTypes;
		d->do_ToolTypes = tt;
		rc = put_es(argv[2], d, FALSE, es);
		d->do_ToolTypes = old;
		Printf("tooltypes=%ld\nsettings=%ld\n", n, nes);
		FreeVec(tt);
		FreeVec(es);
		FreeVec(buf);
		FreeDiskObject(d);
		return rc;
	}
	if (argc >= 3 && !strcmp(argv[1], "loadall"))
	{
		int rounds = argc > 3 ? atol(argv[3]) : 1, loaded = 0, failed = 0;
		struct Screen *scr = LockPubScreen("Workbench");
		struct DateStamp t0, t1;
		APTR ctx;
		DateStamp(&t0);
		for (int r = 0; r < rounds; r++)
		{
			if (!(ctx = ObtainDirContextTags(EX_StringNameInput, argv[2], EX_DataFields, EXF_NAME | EXF_TYPE, TAG_END)))
			{
				Printf("error=dir\n");
				break;
			}
			struct ExamineData *ed;
			while ((ed = ExamineDir(ctx)))
			{
				char path[512];
				size_t l = strlen(ed->Name);
				if (l < 6 || Stricmp(ed->Name + l - 5, ".info")) continue;
				snprintf(path, sizeof(path), "%s/%.*s", argv[2], (int)(l - 5), ed->Name);
				if (getenv("ICONTEST_VERBOSE")) { Printf("load %s\n", path); FFlush(Output()); }
				struct DiskObject *d = GetIconTags(path, ICONGETA_FailIfUnavailable, TRUE, ICONGETA_Screen, scr,
					EMBLEMA_NoCompose, raw, TAG_DONE);
				if (!d) { failed++; continue; }
				if (scr) LayoutIconA(d, scr, NULL);
				FreeDiskObject(d);
				loaded++;
			}
			ReleaseDirContext(ctx);
		}
		DateStamp(&t1);
		if (scr) UnlockPubScreen(NULL, scr);
		int32 ticks = ((t1.ds_Days - t0.ds_Days) * 1440 + t1.ds_Minute - t0.ds_Minute) * 3000 + t1.ds_Tick - t0.ds_Tick;
		Printf("loaded=%ld\nfailed=%ld\nms=%ld\nper_icon_us=%ld\n", loaded, failed, ticks * 20,
			loaded ? ticks * 20000 / loaded : 0);
		return failed ? 5 : 0;
	}
	if (argc >= 4 && !strcmp(argv[1], "leak"))
	{
		int n = atol(argv[3]);
		uint32 before = 0, after, before_s = 0, after_s;
		for (int i = 0; i < 5 + n; i++)
		{
			if (i == 5)
			{
				before = AvailMem(MEMF_PRIVATE);
				before_s = AvailMem(MEMF_SHARED);
			}
			STRPTR fmt = NULL;
			struct DiskObject *d = GetIconTags(argv[2], ICONGETA_FailIfUnavailable, TRUE, ICONGETA_FileFormat, &fmt,
				EMBLEMA_NoCompose, raw, TAG_DONE);
			if (!d) { Printf("error=load\n"); return 10; }
			FreeDiskObject(d);
		}
		after = AvailMem(MEMF_PRIVATE);
		after_s = AvailMem(MEMF_SHARED);
		Printf("private_lost=%ld\nshared_lost=%ld\n", (int32)(before - after), (int32)(before_s - after_s));
		return 0;
	}
	if (argc >= 5 && !strcmp(argv[1], "screen"))
	{
		int depth = atol(argv[2]), secs = atol(argv[3]), first = 4, n = 0, saved = 0;
		BOOL save = FALSE;
		if (!Stricmp(argv[4], "SAVE")) { save = TRUE; first = 5; }
		struct Screen *scr = OpenScreenTags(NULL, SA_LikeWorkbench, TRUE, SA_Depth, depth,
			SA_Title, (uint32)"Emblem icons on a low colour screen", SA_ShowTitle, TRUE, TAG_DONE);
		if (!scr) { Printf("error=screen\n"); return 10; }
		struct DrawInfo *dri = GetScreenDrawInfo(scr);
		struct RastPort *rp = &scr->RastPort;
		Printf("screen_depth=%ld\n", (int32)GetBitMapAttr(scr->RastPort.BitMap, BMA_DEPTH));
		for (int i = first; i < argc; i++, n++)
		{
			STRPTR fmt = NULL;
			struct DiskObject *d = GetIconTags(argv[i], ICONGETA_FailIfUnavailable, TRUE, ICONGETA_Screen, scr,
				ICONGETA_FileFormat, &fmt, EMBLEMA_NoCompose, raw, TAG_DONE);
			if (!d) { Printf("error=load %s\n", argv[i]); continue; }
			LayoutIconA(d, scr, NULL);
			DrawIconState(rp, d, FilePart(argv[i]), 20 + (n % 8) * 100, 40, IDS_NORMAL, ICONDRAWA_DrawInfo, dri, TAG_DONE);
			DrawIconState(rp, d, NULL, 20 + (n % 8) * 100, 160, IDS_SELECTED, ICONDRAWA_DrawInfo, dri, TAG_DONE);
			if (save && PutDiskObject(argv[i], d)) saved++;
			FreeDiskObject(d);
		}
		Printf("drawn=%ld\nsaved=%ld\n", n, saved);
		Delay(secs * 50);
		FreeScreenDrawInfo(scr, dri);
		CloseScreen(scr);
		return 0;
	}
	if (argc >= 4 && !strcmp(argv[1], "pixels"))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		uint32 f = 0, w = 0, h = 0;
		int32 real2 = 0;
		uint8 *d1 = NULL, *d2 = NULL;
		if (!d) return 10;
		IconControl(d, ICONCTRLA_GetImageDataFormat, &f, ICONCTRLA_GetWidth, &w, ICONCTRLA_GetHeight, &h,
			ICONCTRLA_GetImageData1, &d1, ICONCTRLA_GetImageData2, &d2, ICONCTRLA_HasRealImage2, &real2, TAG_DONE);
		for (int i = 0; i < 2; i++)
		{
			uint8 *argb = NULL;
			uint32 iw = w, ih = h;
			if (f == IDFMT_DIRECTMAPPED || f == IDFMT_PALETTEMAPPED)
			{
				uint8 *src = i ? d2 : d1;
				if (!src || (i && !real2)) continue;
				argb = AllocVecTags(w * h * 4, TAG_DONE);
				if (f == IDFMT_DIRECTMAPPED) CopyMem(src, argb, w * h * 4);
				else
				{
					struct ColorRegister *pal = NULL;
					uint32 ps = 0;
					int32 tr = -1;
					IconControl(d, i ? ICONCTRLA_GetPalette2 : ICONCTRLA_GetPalette1, &pal,
						i ? ICONCTRLA_GetPaletteSize2 : ICONCTRLA_GetPaletteSize1, &ps,
						i ? ICONCTRLA_GetTransparentColor2 : ICONCTRLA_GetTransparentColor1, &tr, TAG_DONE);
					cp_from_clut(argb, src, w * h, (uint8 *)pal, ps, (tr >= 0 && tr < (int32)ps) ? tr : -1);
				}
			}
			else
			{
				struct Image *im = i ? ((d->do_Gadget.Flags & GFLG_GADGHIGHBITS) == GFLG_GADGHIMAGE ? d->do_Gadget.SelectRender : NULL)
				                     : d->do_Gadget.GadgetRender;
				if (!im || !im->ImageData) continue;
				iw = im->Width;
				ih = im->Height;
				argb = AllocVecTags(iw * ih * 4, TAG_DONE);
				cp_from_planar(argb, iw, ih, (uint8 *)im->ImageData, im->Depth);
			}
			char path[300];
			snprintf(path, sizeof(path), "%s_%d.argb", argv[3], i + 1);
			BPTR fh = Open(path, MODE_NEWFILE);
			uint8 hdr[8] = { iw >> 24, iw >> 16, iw >> 8, iw, ih >> 24, ih >> 16, ih >> 8, ih };
			if (fh) { Write(fh, hdr, 8); Write(fh, argb, iw * ih * 4); Close(fh); }
			Printf("pixels%ld=%ldx%ld\n", i + 1, iw, ih);
			FreeVec(argb);
		}
		FreeDiskObject(d);
		return 0;
	}
	if (argc >= 3 && !strcmp(argv[1], "setimg"))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		static uint32 a1[20 * 20], a2[20 * 20];
		if (!d) return 10;
		for (int i = 0; i < 20 * 20; i++) { a1[i] = 0xFF102030 + i; a2[i] = 0xFF302010 + i; }
		IconControl(d, ICONCTRLA_SetImageDataFormat, IDFMT_DIRECTMAPPED, ICONCTRLA_SetWidth, 20,
			ICONCTRLA_SetHeight, 20, ICONCTRLA_SetImageData1, a1, ICONCTRLA_SetImageData2, a2, TAG_DONE);
		int rc = put(argv[2], d, FALSE);
		FreeDiskObject(d);
		return rc;
	}
	if (argc >= 4 && !strcmp(argv[1], "bench"))
	{
		int n = atol(argv[3]);
		struct DateStamp t0, t1;
		DateStamp(&t0);
		for (int i = 0; i < n; i++)
		{
			STRPTR fmt = NULL;
			struct DiskObject *d = GetIconTags(argv[2], ICONGETA_FailIfUnavailable, TRUE,
				ICONGETA_FileFormat, &fmt, EMBLEMA_NoCompose, raw, TAG_DONE);
			if (!d) { Printf("error=load\n"); return 10; }
			FreeDiskObject(d);
		}
		DateStamp(&t1);
		int32 ticks = ((t1.ds_Days - t0.ds_Days) * 1440 + t1.ds_Minute - t0.ds_Minute) * 3000 + t1.ds_Tick - t0.ds_Tick;
		Printf("ms=%ld\nper_icon_us=%ld\n", ticks * 20, n ? ticks * 20000 / n : 0);
		return 0;
	}
	if (argc >= 4 && !strcmp(argv[1], "make")) return make(argv[2], argv[3]);
	if (argc >= 4 && (!strcmp(argv[1], "tt") || !strcmp(argv[1], "ttonly")))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		if (!d) return 10;
		BOOL es = !strcmp(argv[1], "tt") && is_setting(argv[3]);
		STRPTR *list = es ? settings : d->do_ToolTypes;
		int n = 0, rc;
		for (STRPTR *tt = list; tt && *tt; tt++) n++;
		STRPTR *nt = AllocVecTags((n + 2) * sizeof(STRPTR), AVT_ClearWithValue, 0, TAG_DONE);
		for (int i = 0; i < n; i++) nt[i] = list[i];
		nt[n] = argv[3];
		if (es)
			rc = put_es(argv[2], d, FALSE, nt);
		else
		{
			STRPTR *old = d->do_ToolTypes;
			d->do_ToolTypes = nt;
			rc = put(argv[2], d, FALSE);
			d->do_ToolTypes = old;
		}
		FreeVec(nt);
		FreeDiskObject(d);
		return rc;
	}
	if (argc >= 5 && !strcmp(argv[1], "pos"))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		if (!d) return 10;
		d->do_CurrentX = atol(argv[3]);
		d->do_CurrentY = atol(argv[4]);
		int rc = put(argv[2], d, TRUE);
		FreeDiskObject(d);
		return rc;
	}
	if (argc >= 4 && !strcmp(argv[1], "layoutsave"))
	{
		/* what Workbench does: load, lay out on the Workbench screen, change, save */
		struct Screen *scr = LockPubScreen("Workbench");
		int32 err = 0;
		struct DiskObject *d = GetIconTags(argv[2], ICONGETA_FailIfUnavailable, TRUE,
			ICONGETA_Screen, scr, ICONA_ErrorCode, &err, TAG_DONE);
		int rc = 10;
		if (d)
		{
			if (scr) LayoutIconA(d, scr, NULL);
			d->do_StackSize = atol(argv[3]);
			rc = put(argv[2], d, FALSE);
			FreeDiskObject(d);
		}
		else
			Printf("error=load %ld\n", err);
		if (scr) UnlockPubScreen(NULL, scr);
		return rc;
	}
	if (argc >= 4 && !strcmp(argv[1], "dup"))
	{
		STRPTR fmt = NULL;
		struct DiskObject *d = load(argv[2], &fmt);
		if (!d) return 10;
		struct DiskObject *c = DupDiskObject(d, TAG_DONE);
		int rc = 10;
		if (c)
		{
			rc = put(argv[3], c, FALSE);
			FreeDiskObject(c);
		}
		else
			Printf("error=dup %ld\n", IoErr());
		FreeDiskObject(d);
		return rc;
	}
	Printf("usage: icontest dump|make|tt|pos|dup ...\n");
	return 20;
}
