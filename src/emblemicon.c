/*
 * EmblemIcon - convert icons between the native Amiga format and the
 * Emblem format of emblem.iconmodule, or show which format they have.
 *
 *   EmblemIcon FILES/M/A,TO/K,ALL/S,QUIET/S
 *
 *   EmblemIcon Work:Prefs                  show format and tool types
 *   EmblemIcon Work:Prefs TO=EMBLEM        convert to the Emblem format
 *   EmblemIcon Work:Prefs TO=AMIGA         convert back to a native icon
 *   EmblemIcon Work:#? TO=EMBLEM           every icon in Work:
 *   EmblemIcon Work: ALL TO=AMIGA          every Emblem icon in Work: and
 *                                          all drawers below, back to native
 *
 * Names may be given with or without ".info" and may be patterns. ALL goes
 * into drawers (not into links). In ALL and pattern runs, icons that already
 * have the wanted format are skipped quietly and only Emblem icons are shown
 * (without TO); a count is printed at the end. The conversion goes through
 * icon.library (PutIconTags with ICONPUTA_FileFormat), so the icon module
 * does the writing. Result code 10 if any file failed, 5 if stopped with
 * Ctrl-C.
 */
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/icon.h>
#include <proto/utility.h>
#include <workbench/icon.h>
#include <string.h>

#include "emblem.h"
#include "EmblemIcon_rev.h"

static const char verstag[] __attribute__((used)) = VERSTAG;

#define TEMPLATE "FILES/M/A,TO/K,ALL/S,QUIET/S"
enum { ARG_FILES, ARG_TO, ARG_ALL, ARG_QUIET, ARG_COUNT };

#define PATHLEN 1024

static CONST_STRPTR to;      /* TO=, or NULL */
static BOOL quiet, all;
static BOOL many;            /* a pattern or ALL run */
static BOOL stopped;
static uint32 nfound, ndone, nfailed;

static const char *fmtname(uint32 f)
{
	return f == IDFMT_DIRECTMAPPED ? "ARGB" : f == IDFMT_PALETTEMAPPED ? "palette" : "planar";
}

static struct DiskObject *load(CONST_STRPTR name, STRPTR *fmt, int32 *err)
{
	*fmt = NULL;
	*err = 0;
	return GetIconTags(name,
		ICONGETA_FailIfUnavailable, TRUE,
		ICONGETA_RemapIcon,         FALSE,
		ICONGETA_GenerateImageMasks, FALSE,
		ICONGETA_FileFormat,        fmt,
		ICONA_ErrorCode,            err,
		EMBLEMA_NoCompose,          TRUE,   /* the icon's own images, never a default image */
		TAG_DONE);
}

/* 1 if the file starts like an Emblem file (FORM....EMBL) */
static BOOL is_emblem_file(CONST_STRPTR info)
{
	uint8 b[12];
	BOOL r = FALSE;
	BPTR fh = Open(info, MODE_OLDFILE);
	if (fh)
	{
		r = Read(fh, b, 12) == 12 && !memcmp(b, "FORM", 4) && !memcmp(b + 8, "EMBL", 4);
		Close(fh);
	}
	return r;
}

static int do_file(CONST_STRPTR arg)
{
	char name[1024];
	STRPTR fmt;
	int32 err;
	struct DiskObject *dobj;
	size_t len;

	strlcpy(name, arg, sizeof(name));
	len = strlen(name);
	if (len > 5 && Stricmp(name + len - 5, ".info") == 0)
		name[len - 5] = 0;

	if (many)
	{
		/* only Emblem icons are shown or converted back; only native ones converted */
		char info[PATHLEN + 8];
		strlcpy(info, name, sizeof(info));
		strlcat(info, ".info", sizeof(info));
		BOOL emb = is_emblem_file(info);
		if ((!to || Stricmp(to, "AMIGA") == 0) ? !emb : emb) return 0;
		nfound++;
	}

	if (!(dobj = load(name, &fmt, &err)))
	{
		char msg[100];
		Fault(err ? err : ERROR_OBJECT_NOT_FOUND, NULL, msg, sizeof(msg));
		Printf("Error: %s.info: %s\n", name, msg);
		return 10;
	}

	if (!to)
	{
		uint32 w = 0, h = 0, f = IDFMT_BITMAPPED, n = 0;
		IconControl(dobj, ICONCTRLA_GetWidth, &w, ICONCTRLA_GetHeight, &h,
			ICONCTRLA_GetImageDataFormat, &f, TAG_DONE);
		for (STRPTR *tt = dobj->do_ToolTypes; tt && *tt; tt++) n++;
		Printf("%s.info: %s format, %s image", name, fmt ? fmt : (STRPTR)"?", fmtname(f));
		if (f != IDFMT_BITMAPPED) Printf(" %lux%lu", w, h);
		Printf(", %lu tool type%s\n", n, n == 1 ? "" : "s");
		if (!quiet)
			for (STRPTR *tt = dobj->do_ToolTypes; tt && *tt; tt++)
				Printf("  %s\n", *tt);
		FreeDiskObject(dobj);
		return 0;
	}

	BOOL toemblem = Stricmp(to, "EMBLEM") == 0;
	if (fmt && Stricmp(fmt, toemblem ? "Emblem" : "Amiga") == 0)
	{
		if (!quiet && !many) Printf("%s.info: already %s\n", name, fmt);
		FreeDiskObject(dobj);
		return 0;
	}

	err = 0;
	BOOL ok = PutIconTags(name, dobj,
		ICONPUTA_FileFormat,      toemblem ? (uint32)"Emblem" : ~0UL,
		ICONPUTA_NoFallback,      TRUE,
		ICONPUTA_NotifyWorkbench, TRUE,
		ICONA_ErrorCode,          &err,
		TAG_DONE);
	FreeDiskObject(dobj);
	if (!ok)
	{
		char msg[100];
		Fault(err ? err : IoErr(), NULL, msg, sizeof(msg));
		Printf("Error: %s.info: not saved: %s%s\n", name, msg,
			toemblem ? " (is emblem.iconmodule installed?)" : "");
		return 10;
	}

	/* check what is on disk now */
	if (!(dobj = load(name, &fmt, &err)))
	{
		Printf("Error: %s.info: saved, but can't be loaded again\n", name);
		return 10;
	}
	if (!fmt || Stricmp(fmt, toemblem ? "Emblem" : "Amiga") != 0)
	{
		Printf("Error: %s.info: saved as %s instead\n", name, fmt ? fmt : (STRPTR)"?");
		FreeDiskObject(dobj);
		return 10;
	}
	if (!quiet) Printf("%s.info: converted to %s\n", name, fmt);
	FreeDiskObject(dobj);
	ndone++;
	return 0;
}

static BOOL has_suffix(CONST_STRPTR s, CONST_STRPTR suf)
{
	size_t a = strlen(s), b = strlen(suf);
	return a > b && Stricmp(s + a - b, suf) == 0;
}

static int one(CONST_STRPTR path)
{
	int r = do_file(path);
	if (r) nfailed++;
	return r;
}

static BOOL check_break(void)
{
	if (!stopped && CheckSignal(SIGBREAKF_CTRL_C))
	{
		PrintFault(ERROR_BREAK, NULL);
		stopped = TRUE;
	}
	return stopped;
}

/* Every .info file in dir and, with ALL, in the drawers below (not links). */
static int walk(CONST_STRPTR dir)
{
	APTR ctx = ObtainDirContextTags(EX_StringNameInput, dir,
		EX_DataFields, EXF_NAME | EXF_LINK | EXF_TYPE, TAG_END);
	struct ExamineData *dat;
	char path[PATHLEN];
	int rc = 0, r;

	if (!ctx)
	{
		PrintFault(IoErr(), dir);
		nfailed++;
		return 10;
	}
	while (!check_break() && (dat = ExamineDir(ctx)))
	{
		if (EXD_IS_LINK(dat)) continue;
		strlcpy(path, dir, sizeof(path));
		if (!AddPart(path, dat->Name, sizeof(path)))
		{
			Printf("Error: name too long in %s\n", dir);
			rc = 10;
			continue;
		}
		if (EXD_IS_FILE(dat) && has_suffix(dat->Name, ".info"))
			r = one(path);
		else if (EXD_IS_DIRECTORY(dat) && all)
			r = walk(path);
		else
			continue;
		if (r > rc) rc = r;
	}
	if (!stopped && IoErr() != ERROR_NO_MORE_ENTRIES)
	{
		PrintFault(IoErr(), dir);
		rc = 10;
	}
	ReleaseDirContext(ctx);
	return rc;
}

static BOOL is_dir(CONST_STRPTR name)
{
	struct ExamineData *dat = ExamineObjectTags(EX_StringNameInput, name, TAG_END);
	BOOL r = dat && EXD_IS_DIRECTORY(dat);
	if (dat) FreeDosObject(DOS_EXAMINEDATA, dat);
	return r;
}

static BOOL exists(CONST_STRPTR name)
{
	BPTR l = Lock(name, SHARED_LOCK);
	if (l) UnLock(l);
	return l != ZERO;
}

/* One FILES argument: a pattern, an icon (with or without .info) or, with
 * ALL, a drawer or volume. */
static int do_arg(CONST_STRPTR arg)
{
	char pat[PATHLEN * 2 + 2];
	int rc = 0, r;

	if (ParsePatternNoCase(arg, pat, sizeof(pat)) == 1)
	{
		struct AnchorPath *ap = AllocDosObjectTags(DOS_ANCHORPATH, ADO_Strlen, PATHLEN,
			ADO_Mask, SIGBREAKF_CTRL_C, TAG_END);
		int32 e;
		if (!ap) return 20;
		many = TRUE;
		for (e = MatchFirst(arg, ap); e == 0 && !check_break(); e = MatchNext(ap))
		{
			BOOL dir = ap->ap_ExData ? EXD_IS_DIRECTORY(ap->ap_ExData) : ap->ap_Info.fib_DirEntryType > 0;
			if (!dir && has_suffix(ap->ap_Buffer, ".info")) r = one(ap->ap_Buffer);
			else if (dir && all) r = walk(ap->ap_Buffer);
			else continue;
			if (r > rc) rc = r;
		}
		if (!stopped && e == ERROR_BREAK)
		{
			PrintFault(ERROR_BREAK, NULL);
			stopped = TRUE;
		}
		else if (!stopped && e != ERROR_NO_MORE_ENTRIES)
		{
			PrintFault(e, arg);
			rc = 10;
		}
		MatchEnd(ap);
		FreeDosObject(DOS_ANCHORPATH, ap);
		return rc;
	}

	if (all && is_dir(arg))
	{
		char info[PATHLEN];
		size_t n = strlen(arg);
		many = TRUE;
		/* the drawer's own icon (not for a volume or assign: "Work:") */
		if (n && arg[n - 1] != ':' && arg[n - 1] != '/')
		{
			strlcpy(info, arg, sizeof(info));
			strlcat(info, ".info", sizeof(info));
			if (exists(info) && (r = one(arg)) > rc) rc = r;
		}
		if ((r = walk(arg)) > rc) rc = r;
		return rc;
	}
	return one(arg);
}

int main(void)
{
	int32 args[ARG_COUNT] = { 0 };
	struct RDArgs *rda = ReadArgs(TEMPLATE, args, NULL);
	int rc = 0;

	if (!rda)
	{
		PrintFault(IoErr(), "EmblemIcon");
		return 20;
	}
	to = (CONST_STRPTR)args[ARG_TO];
	quiet = args[ARG_QUIET] != 0;
	all = args[ARG_ALL] != 0;
	if (to && Stricmp(to, "EMBLEM") != 0 && Stricmp(to, "AMIGA") != 0)
	{
		Printf("Error: TO must be EMBLEM or AMIGA\n");
		FreeArgs(rda);
		return 20;
	}
	for (STRPTR *f = (STRPTR *)args[ARG_FILES]; *f && !check_break(); f++)
	{
		int r = do_arg(*f);
		if (r > rc) rc = r;
	}
	if (many)
	{
		if (to) Printf("%lu icon%s converted to %s", ndone, ndone == 1 ? "" : "s",
			Stricmp(to, "EMBLEM") == 0 ? "Emblem" : "Amiga");
		else Printf("%lu Emblem icon%s", nfound, nfound == 1 ? "" : "s");
		if (nfailed) Printf(", %lu failed", nfailed);
		Printf("\n");
	}
	if (stopped && rc < 5) rc = 5;
	FreeArgs(rda);
	return rc;
}
