/*
 * EmblemIcon - convert icons between the native Amiga format and the
 * Emblem format of emblem.iconmodule, or show which format they have.
 *
 *   EmblemIcon FILES/M/A,TO/K,ALL/S,TYPE/K,SET/K,UNSET/K,QUIET/S
 *
 *   EmblemIcon Work:Prefs                  show format and tool types
 *   EmblemIcon Work:Prefs TO=EMBLEM        convert to the Emblem format
 *   EmblemIcon Work:Prefs TO=AMIGA         convert back to a native icon
 *   EmblemIcon Work:#? TO=EMBLEM           every icon in Work:
 *   EmblemIcon Work: ALL TO=AMIGA          every Emblem icon in Work: and
 *                                          all drawers below, back to native
 *   EmblemIcon Work: ALL TYPE=DRAWER TO=EMBLEM SET="IMAGE=Drawer|EMBLEM=INTERNAL,30,30,33,30"
 *                                          every drawer icon: Emblem, with
 *                                          these tool types
 *   EmblemIcon Work: ALL TO=AMIGA UNSET="IMAGE|EMBLEM"
 *                                          back, without those tool types
 *
 * Names may be given with or without ".info" and may be patterns. ALL goes
 * into drawers (not into links). In ALL and pattern runs, icons that already
 * have the wanted format are skipped quietly and only Emblem icons are shown
 * (without TO); a count is printed at the end.
 *
 * SET sets tool types ("KEY=value", several separated by '|'): the first one
 * with that key (case ignored, like FindToolType()) is replaced and later ones
 * with the same key removed; a new key is added at the end. UNSET removes all
 * tool types with the given keys (separated by '|'); it is done before SET.
 * With SET or UNSET, Emblem icons are changed too in TO=EMBLEM runs, and
 * without TO only Emblem icons are changed in ALL and pattern runs. TYPE
 * (DISK, DRAWER, TOOL, PROJECT, GARBAGE, DEVICE, KICK; several separated by
 * commas) limits everything to icons of those types.
 *
 * Saving goes through icon.library (PutIconTags with ICONPUTA_FileFormat), so
 * the icon module does the writing; every saved icon is loaded again and
 * checked. Result code 10 if any file failed, 5 if stopped with Ctrl-C, 20 for
 * bad arguments.
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

#define TEMPLATE "FILES/M/A,TO/K,ALL/S,TYPE/K,SET/K,UNSET/K,QUIET/S"
enum { ARG_FILES, ARG_TO, ARG_ALL, ARG_TYPE, ARG_SET, ARG_UNSET, ARG_QUIET, ARG_COUNT };

#define PATHLEN 1024
#define MAXTT   32           /* SET / UNSET entries */

static CONST_STRPTR to;      /* TO=, or NULL */
static BOOL quiet, all;
static BOOL many;            /* a pattern or ALL run */
static BOOL stopped;
static uint32 nfound, nconverted, nchanged, nfailed;
static STRPTR sets[MAXTT], unsets[MAXTT];
static int nsets, nunsets;
static uint32 types;         /* TYPE=: bit n = do_Type n; 0 = all */

static const char *const typenames[] = { NULL, "DISK", "DRAWER", "TOOL", "PROJECT", "GARBAGE", "DEVICE", "KICK" };

/* length of a tool type's key: up to '=' or the whole string */
static size_t keylen(CONST_STRPTR s)
{
	const char *e = strchr(s, '=');
	return e ? (size_t)(e - s) : strlen(s);
}

static BOOL same_key(CONST_STRPTR a, CONST_STRPTR b)
{
	size_t n = keylen(a);
	return n == keylen(b) && Strnicmp(a, b, n) == 0;
}

/* Split a '|' separated list (in place, the string stays alive) into out[];
 * spaces round each entry are dropped. Returns the count, -1 if too many. */
static int split(STRPTR s, STRPTR *out)
{
	int n = 0;
	while (s && *s)
	{
		STRPTR e = strchr(s, '|'), end;
		if (e) *e = 0;
		while (*s == ' ') s++;
		end = s + strlen(s);
		while (end > s && end[-1] == ' ') *--end = 0;
		if (*s)
		{
			if (n == MAXTT) return -1;
			out[n++] = s;
		}
		s = e ? e + 1 : NULL;
	}
	return n;
}

/* The icon's tool types with UNSET and SET applied: a new NULL-terminated
 * array (FreeVec it) of pointers into the old strings and sets[]; *changed
 * tells whether it differs from the old one. NULL if out of memory. */
static STRPTR *new_tooltypes(STRPTR *old, BOOL *changed)
{
	int n = 0, k = 0, i, j;
	STRPTR *tt;
	for (STRPTR *p = old; p && *p; p++) n++;
	if (!(tt = AllocVecTags((n + nsets + 1) * sizeof(STRPTR), AVT_ClearWithValue, 0, TAG_DONE)))
		return NULL;
	for (i = 0; i < n; i++)
	{
		BOOL drop = FALSE;
		for (j = 0; j < nunsets && !drop; j++)
			drop = same_key(old[i], unsets[j]);
		if (!drop) tt[k++] = old[i];
	}
	for (j = 0; j < nsets; j++)
	{
		int first = -1;
		for (i = 0; i < k; i++)
		{
			if (!same_key(tt[i], sets[j])) continue;
			if (first < 0)
			{
				first = i;
				tt[i] = sets[j];
			}
			else
			{
				memmove(&tt[i], &tt[i + 1], (k - i - 1) * sizeof(STRPTR));
				k--;
				i--;
			}
		}
		if (first < 0) tt[k++] = sets[j];
	}
	tt[k] = NULL;
	*changed = k != n;
	for (i = 0; i < k && !*changed; i++)
		*changed = strcmp(tt[i], old[i]) != 0;
	return tt;
}

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

	BOOL edit = nsets || nunsets;
	if (many)
	{
		/* Emblem icons are shown, changed and converted back; native ones are
		 * converted (with SET/UNSET Emblem ones are changed too) */
		char info[PATHLEN + 8];
		strlcpy(info, name, sizeof(info));
		strlcat(info, ".info", sizeof(info));
		BOOL emb = is_emblem_file(info);
		BOOL want = (!to || Stricmp(to, "AMIGA") == 0) ? emb : (edit || !emb);
		if (!want) return 0;
	}

	if (!(dobj = load(name, &fmt, &err)))
	{
		char msg[100];
		Fault(err ? err : ERROR_OBJECT_NOT_FOUND, NULL, msg, sizeof(msg));
		Printf("Error: %s.info: %s\n", name, msg);
		return 10;
	}

	if (types && !(dobj->do_Type < 32 && (types & (1UL << dobj->do_Type))))
	{
		if (!quiet && !many) Printf("%s.info: skipped (type %s)\n", name,
			dobj->do_Type < 8 && typenames[dobj->do_Type] ? typenames[dobj->do_Type] : "?");
		FreeDiskObject(dobj);
		return 0;
	}
	nfound++;

	if (!to && !edit)
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

	/* the format to save in: TO=, else the icon's own */
	char target[32];
	if (to) strlcpy(target, Stricmp(to, "EMBLEM") == 0 ? "Emblem" : "Amiga", sizeof(target));
	else strlcpy(target, fmt ? (CONST_STRPTR)fmt : (CONST_STRPTR)"Amiga", sizeof(target));
	BOOL convert = !fmt || Stricmp(fmt, target) != 0;

	BOOL ttchanged = FALSE;
	STRPTR *newtt = NULL, *oldtt = dobj->do_ToolTypes;
	if (edit && !(newtt = new_tooltypes(oldtt, &ttchanged)))
	{
		Printf("Error: %s.info: out of memory\n", name);
		FreeDiskObject(dobj);
		return 10;
	}
	if (!convert && !ttchanged)
	{
		if (!quiet && !many)
		{
			if (edit) Printf("%s.info: no change\n", name);
			else Printf("%s.info: already %s\n", name, fmt);
		}
		FreeVec(newtt);
		FreeDiskObject(dobj);
		return 0;
	}

	BOOL toemblem = Stricmp(target, "Emblem") == 0;
	if (newtt) dobj->do_ToolTypes = newtt;
	err = 0;
	BOOL ok = PutIconTags(name, dobj,
		ICONPUTA_FileFormat,      Stricmp(target, "Amiga") == 0 ? ~0UL : (uint32)target,
		ICONPUTA_NoFallback,      TRUE,
		ICONPUTA_NotifyWorkbench, TRUE,
		ICONA_ErrorCode,          &err,
		TAG_DONE);
	dobj->do_ToolTypes = oldtt;
	FreeVec(newtt);
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
	if (!fmt || Stricmp(fmt, target) != 0)
	{
		Printf("Error: %s.info: saved as %s instead\n", name, fmt ? fmt : (STRPTR)"?");
		FreeDiskObject(dobj);
		return 10;
	}
	for (int i = 0; i < nsets; i++)
	{
		char key[128];
		size_t kl = keylen(sets[i]);
		STRPTR v;
		strlcpy(key, sets[i], kl + 1 < sizeof(key) ? kl + 1 : sizeof(key));
		if (!(v = FindToolType(dobj->do_ToolTypes, key)) || strcmp(v, sets[i] + kl + 1) != 0)
		{
			Printf("Error: %s.info: tool type %s not saved\n", name, key);
			FreeDiskObject(dobj);
			return 10;
		}
	}
	for (int i = 0; i < nunsets; i++)
		for (STRPTR *p = dobj->do_ToolTypes; p && *p; p++)
			if (same_key(*p, unsets[i]))
			{
				Printf("Error: %s.info: tool type %s not removed\n", name, unsets[i]);
				FreeDiskObject(dobj);
				return 10;
			}
	if (!quiet)
	{
		if (convert && ttchanged) Printf("%s.info: converted to %s, tool types changed\n", name, fmt);
		else if (convert) Printf("%s.info: converted to %s\n", name, fmt);
		else Printf("%s.info: tool types changed\n", name);
	}
	FreeDiskObject(dobj);
	if (convert) nconverted++;
	if (ttchanged) nchanged++;
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
	if (args[ARG_SET] && (nsets = split((STRPTR)args[ARG_SET], sets)) < 0)
	{
		Printf("Error: more than %ld SET entries\n", (int32)MAXTT);
		FreeArgs(rda);
		return 20;
	}
	for (int i = 0; i < nsets; i++)
		if (keylen(sets[i]) == 0 || !strchr(sets[i], '='))
		{
			Printf("Error: SET entries must be KEY=value: %s\n", sets[i]);
			FreeArgs(rda);
			return 20;
		}
	if (args[ARG_UNSET] && (nunsets = split((STRPTR)args[ARG_UNSET], unsets)) < 0)
	{
		Printf("Error: more than %ld UNSET entries\n", (int32)MAXTT);
		FreeArgs(rda);
		return 20;
	}
	if (args[ARG_TYPE])
	{
		STRPTR t = (STRPTR)args[ARG_TYPE];
		while (*t)
		{
			char word[16];
			size_t n = strcspn(t, ",");
			int k;
			strlcpy(word, t, n + 1 < sizeof(word) ? n + 1 : sizeof(word));
			for (k = 1; k < 8 && Stricmp(word, typenames[k]) != 0; k++) ;
			if (k == 8)
			{
				Printf("Error: TYPE must be DISK, DRAWER, TOOL, PROJECT, GARBAGE, DEVICE or KICK: %s\n", word);
				FreeArgs(rda);
				return 20;
			}
			types |= 1UL << k;
			t += n;
			if (*t == ',') t++;
		}
	}
	for (STRPTR *f = (STRPTR *)args[ARG_FILES]; *f && !check_break(); f++)
	{
		int r = do_arg(*f);
		if (r > rc) rc = r;
	}
	if (many)
	{
		if (to)
			Printf("%lu icon%s converted to %s", nconverted, nconverted == 1 ? "" : "s",
				Stricmp(to, "EMBLEM") == 0 ? "Emblem" : "Amiga");
		else if (!nsets && !nunsets)
			Printf("%lu Emblem icon%s", nfound, nfound == 1 ? "" : "s");
		if (nsets || nunsets)
			Printf("%s%lu with changed tool types", to ? ", " : "", nchanged);
		if (nfailed) Printf(", %lu failed", nfailed);
		Printf("\n");
	}
	if (stopped && rc < 5) rc = 5;
	FreeArgs(rda);
	return rc;
}
