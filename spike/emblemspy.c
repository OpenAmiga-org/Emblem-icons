/*
 * emblemspy.iconmodule - feasibility spike for the Emblem icon plugin.
 *
 * A do-nothing icon module: it logs every call icon.library makes
 * (DebugPrintF) and always answers "not my format", so icons load as
 * before. Goal: find out whether icon.library asks modules about
 * ordinary .info files (native Amiga format), and in which order.
 */

#include <exec/exec.h>
#include <exec/interfaces.h>
#include <exec/resident.h>
#include <dos/dos.h>
#include <workbench/icon.h>
#include <workbench/iconmodule.h>
#include <interfaces/iconmodule.h>
#include <proto/exec.h>
#include <proto/utility.h>
#include <stdarg.h>

/* GCC 15: the SDK macro passes &ap, the builtin wants the decayed va_list */
#define LINEARTAGS(ap) ((struct TagItem *)__builtin_getlinearva(ap))

#define LIBNAME  "emblemspy.iconmodule"
#define VERSION  1
#define REVISION 0

static const char verstag[] = "\0$VER: emblemspy.iconmodule 1.0 (15.11.2026)";

struct ModBase
{
	struct Library lib;
	BPTR           seglist;
};

struct ExecIFace    *IExec;
struct Library      *UtilityBase;
struct UtilityIFace *IUtility;
static struct IconIFace *SpyIIcon;
static uint32 LoadCalls;

int32 _start(void) { return -1; }

static CONST_STRPTR taskname(void)
{
	struct Task *t = IExec->FindTask(NULL);
	return (t && t->tc_Node.ln_Name) ? (CONST_STRPTR)t->tc_Node.ln_Name : (CONST_STRPTR)"?";
}

static void seterr(struct TagItem *tags, int32 err)
{
	int32 *p = (int32 *)IUtility->GetTagData(IMA_ErrorCode, 0, tags);
	if (p) *p = err;
}

/* ---- main interface ---- */

static uint32 APICALL m_Obtain(struct IconModuleIFace *Self) { return ++Self->Data.RefCount; }
static uint32 APICALL m_Release(struct IconModuleIFace *Self) { return --Self->Data.RefCount; }

static CONST_STRPTR FormatNames[] = { "EmblemSpy", NULL };
static CONST_STRPTR FormatDescs[] = { "Emblem spike (logs only)", NULL };

static uint32 APICALL m_ModuleControlA(struct IconModuleIFace *Self, APTR object, struct TagItem *tags)
{
	struct TagItem *state = tags, *ti;
	uint32 n = 0;
	int32 err = 0;

	IExec->DebugPrintF("[emblemspy] ModuleControlA obj=%p task=%s\n", object, taskname());
	while ((ti = IUtility->NextTagItem(&state)))
	{
		switch (ti->ti_Tag)
		{
			case IMA_ErrorCode:          break;
			case IMA_ErrorTagItem:       *(struct TagItem **)ti->ti_Data = NULL; break;
			case IMA_GetFormatNames:     *(CONST_STRPTR **)ti->ti_Data = FormatNames; break;
			case IMA_GetFormatDescs:     *(CONST_STRPTR **)ti->ti_Data = FormatDescs; break;
			case IMA_SetIconBase:        break;
			case IMA_SetIconIFace:       SpyIIcon = (struct IconIFace *)ti->ti_Data; break;
			case IMA_SetMaxUnknownDataSize: break;
			case IMA_GetLoadSupport:     *(uint32 *)ti->ti_Data = TRUE; break;
			case IMA_GetSaveSupport:     *(uint32 *)ti->ti_Data = FALSE; break;
			case IMA_GetScaleSupport:    *(uint32 *)ti->ti_Data = FALSE; break;
			case IMA_GetConvertSupport:  *(uint32 *)ti->ti_Data = FALSE; break;
			case IMA_GetFileFormat:      err = ERROR_OBJECT_WRONG_TYPE; break;
			default:
				IExec->DebugPrintF("[emblemspy]   unknown tag 0x%08lx\n", ti->ti_Tag);
				break;
		}
		IExec->DebugPrintF("[emblemspy]   tag IMA+%ld\n", (int32)(ti->ti_Tag - IMA_Dummy));
		if (err) break;
		n++;
	}
	seterr(tags, err);
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
	LoadCalls++;
	IExec->DebugPrintF("[emblemspy] LoadIconA #%lu '%s' icon=%p task=%s\n",
		LoadCalls, name ? name : (CONST_STRPTR)"(null)", icon, taskname());
	seterr(tags, ERROR_OBJECT_WRONG_TYPE);
	return NULL;
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
	IExec->DebugPrintF("[emblemspy] SaveIconA '%s' fmt=%s task=%s\n", name ? name : (CONST_STRPTR)"(null)",
		(CONST_STRPTR)IUtility->GetTagData(IMA_SaveFormat, (uint32)"(none)", tags), taskname());
	seterr(tags, ERROR_OBJECT_WRONG_TYPE);
	return FALSE;
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
	IExec->DebugPrintF("[emblemspy] AllocIconDataA %p\n", icon);
	seterr(tags, ERROR_NOT_IMPLEMENTED);
	return FALSE;
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
	IExec->DebugPrintF("[emblemspy] FreeIconDataA %p\n", icon);
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
	IExec->DebugPrintF("[emblemspy] DupIconDataA %p\n", icon);
	seterr(tags, 0);
	return NULL;
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
	IExec->DebugPrintF("[emblemspy] ScaleIconA %p\n", icon);
	seterr(tags, ERROR_NOT_IMPLEMENTED);
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

static BPTR APICALL lm_Expunge(struct LibraryManagerInterface *Self)
{
	struct ModBase *base = (struct ModBase *)Self->Data.LibBase;
	BPTR seg = 0;
	if (base->lib.lib_OpenCnt == 0)
	{
		seg = base->seglist;
		IExec->DebugPrintF("[emblemspy] expunged\n");
		IExec->Remove(&base->lib.lib_Node);
		if (IUtility) IExec->DropInterface((struct Interface *)IUtility);
		if (UtilityBase) IExec->CloseLibrary(UtilityBase);
		IExec->DeleteLibrary(&base->lib);
	}
	else
		base->lib.lib_Flags |= LIBF_DELEXP;
	return seg;
}

static struct Library * APICALL lm_Open(struct LibraryManagerInterface *Self, uint32 version)
{
	struct Library *lib = Self->Data.LibBase;
	lib->lib_OpenCnt++;
	lib->lib_Flags &= ~LIBF_DELEXP;
	IExec->DebugPrintF("[emblemspy] opened by %s (cnt %ld)\n", taskname(), (int32)lib->lib_OpenCnt);
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
	struct ModBase *base = (struct ModBase *)lib;

	IExec = iexec;
	lib->lib_Node.ln_Type = NT_LIBRARY;
	lib->lib_Node.ln_Pri  = 0;
	lib->lib_Node.ln_Name = (STRPTR)LIBNAME;
	lib->lib_Flags        = LIBF_SUMUSED | LIBF_CHANGED;
	lib->lib_Version      = VERSION;
	lib->lib_Revision     = REVISION;
	lib->lib_IdString     = (STRPTR)(verstag + 7);
	base->seglist = seglist;

	UtilityBase = IExec->OpenLibrary("utility.library", 50);
	IUtility = UtilityBase ? (struct UtilityIFace *)IExec->GetInterface(UtilityBase, "main", 1, NULL) : NULL;
	if (!IUtility)
	{
		if (UtilityBase) IExec->CloseLibrary(UtilityBase);
		return NULL;
	}
	IExec->DebugPrintF("[emblemspy] init\n");
	return lib;
}

static const struct TagItem libCreateTags[] =
{
	{ CLT_DataSize,   sizeof(struct ModBase) },
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
	(STRPTR)(verstag + 7),
	(APTR)libCreateTags
};
