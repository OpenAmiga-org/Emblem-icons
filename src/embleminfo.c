/*
 * EmblemInfo - edit an icon's Emblem settings (docs/embleminfo.md).
 *
 *   EmblemInfo FILES/M,PUBSCREEN/K
 *
 * One window per icon (one after the other): a preview (made by the module itself), the
 * default image and selected image, the emblem and selected emblem (file, the icon's own
 * picture, size, position, effect), and the format (normal icon or Emblem icon). From
 * Workbench: shift-select icons and double-click EmblemInfo; without icons it asks for one.
 *
 * The icon is loaded with EMBLEMA_NoCompose (its own images) and EMBLEMA_GetSettings,
 * and saved with PutIconTags(ICONPUTA_FileFormat, EMBLEMA_SetSettings); everything else
 * in it (tool types, position, own images) stays as it is. Public domain.
 */
#define ALL_REACTION_CLASSES
#include <reaction/reaction.h>
#include <reaction/reaction_macros.h>
#include <proto/exec.h>
#include <proto/dos.h>
#include <proto/intuition.h>
#include <proto/icon.h>
#include <proto/asl.h>
#include <proto/utility.h>
#include <proto/graphics.h>
#include <intuition/gadgetclass.h>
#include <workbench/startup.h>
#include <workbench/icon.h>
#include <libraries/asl.h>
#include <string.h>
#include <stdio.h>

#include "emblem.h"
#include "emblemspec.h"
#include "EmblemInfo_rev.h"

static const char verstag[] __attribute__((used)) = VERSTAG;

#define PATHLEN  1024
#define MAXEXTRA 32           /* settings with other keys, kept as they are */
#define APPNAME  "EmblemInfo"

enum
{
	GID_FORMAT, GID_PREV1, GID_PREV2,
	/* image, selected image: name, file button, effect */
	GID_IMG, GID_IMG_POP, GID_IMG_EFF,
	GID_SIMG, GID_SIMG_POP, GID_SIMG_EFF,
	/* emblem, selected emblem: name, file button, own picture, w, h, x, y, effect */
	GID_EM, GID_EM_POP, GID_EM_OWN, GID_EM_W, GID_EM_H, GID_EM_X, GID_EM_Y, GID_EM_EFF,
	GID_SEM_SAME,
	GID_SEM, GID_SEM_POP, GID_SEM_OWN, GID_SEM_W, GID_SEM_H, GID_SEM_X, GID_SEM_Y, GID_SEM_EFF,
	GID_SAVE, GID_CANCEL, GID_COUNT
};

/* first gadget of an emblem's row of fields (emblem 0 / selected emblem 1) */
#define EMG(i, k) ((i) ? GID_SEM + (k) : GID_EM + (k))
enum { EF_NAME, EF_POP, EF_OWN, EF_W, EF_H, EF_X, EF_Y, EF_EFF };

static CONST_STRPTR effects[] = { "Settings file", "None", "Shadow", "Glow", "Gray", "Dark", "Bright", NULL };
static CONST_STRPTR formats[] = { "Normal icon", "Emblem icon", NULL };
static CONST_STRPTR methodword[] = { "", "NONE", "SHADOW", "GLOW", "GRAY", "DARK", "BRIGHT" };

typedef struct Edit
{
	char               name[PATHLEN];      /* the icon, without ".info" */
	struct Screen     *scr;
	struct DiskObject *own;                /* loaded with EMBLEMA_NoCompose: its own images */
	struct DiskObject *preview;            /* composed, laid out on scr */
	BOOL               wasemblem;
	char               tmp[64];            /* T: file of the preview */
	STRPTR             extra[MAXEXTRA];    /* other settings (copies) */
	int                nextra;
	Object            *win;
	struct Window     *window;
	Object            *g[GID_COUNT];
	struct Hook        render[2];
	char               imgdir[PATHLEN];    /* ENVARC:sys/emblem, as a full path */
	char               title[PATHLEN + 32]; /* the window keeps a pointer to it */
} Edit;

/* ---- small helpers ---- */

static void request(Edit *e, CONST_STRPTR text, CONST_STRPTR buttons, int32 *answer)
{
	struct EasyStruct es = { sizeof(struct EasyStruct), 0, APPNAME, text, buttons };
	int32 r = EasyRequest(e && e->window ? e->window : NULL, &es, NULL);
	if (answer) *answer = r;
}

static uint32 getv(Edit *e, int id, uint32 attr)
{
	uint32 v = 0;
	GetAttr(attr, e->g[id], &v);
	return v;
}

static void setv(Edit *e, int id, uint32 attr, uint32 v)
{
	SetGadgetAttrs((struct Gadget *)e->g[id], e->window, NULL, attr, v, TAG_DONE);
}

static BOOL has_key(CONST_STRPTR s)
{
	static const char *const keys[] = { "IMAGE", "IMAGESELECTED", "EMBLEM", "EMBLEMSELECTED" };
	const char *eq = strchr(s, '=');
	size_t n = eq ? (size_t)(eq - s) : strlen(s);
	for (int i = 0; i < 4; i++)
		if (n == strlen(keys[i]) && Strnicmp(s, keys[i], n) == 0) return TRUE;
	return FALSE;
}

/* ---- settings <-> gadgets ---- */

/* The gadgets' values as settings strings in buf (NUL-separated), pointers in arr. */
static void build_settings(Edit *e, char *buf, size_t bufsize, STRPTR *arr)
{
	size_t pos = 0;
	int n = 0;
	char s[ES_NAMELEN * 2 + 64];

	for (int i = 0; i < e->nextra; i++)
		arr[n++] = e->extra[i];
	for (int i = 0; i < 2; i++)
	{
		STRPTR name = (STRPTR)getv(e, i ? GID_SIMG : GID_IMG, STRINGA_TextVal);
		uint32 m = getv(e, i ? GID_SIMG_EFF : GID_IMG_EFF, CHOOSER_Selected);
		if (!name || !*name) continue;
		snprintf(s, sizeof(s), "%s=%s%s%s", i ? "IMAGESELECTED" : "IMAGE", name, m ? "," : "", m < 7 ? methodword[m] : "");
		if (pos + strlen(s) + 1 > bufsize) break;
		strcpy(buf + pos, s);
		arr[n++] = buf + pos;
		pos += strlen(s) + 1;
	}
	for (int i = 0; i < 2; i++)
	{
		int k = i && getv(e, GID_SEM_SAME, GA_Selected) ? 0 : i;   /* "same as the emblem" */
		BOOL own = getv(e, EMG(k, EF_OWN), GA_Selected);
		STRPTR name = own ? (STRPTR)"INTERNAL" : (STRPTR)getv(e, EMG(k, EF_NAME), STRINGA_TextVal);
		uint32 m = getv(e, EMG(k, EF_EFF), CHOOSER_Selected);
		if (!name || !*name) continue;
		snprintf(s, sizeof(s), "%s=%s,%ld,%ld,%ld,%ld%s%s", i ? "EMBLEMSELECTED" : "EMBLEM", name,
			(int32)getv(e, EMG(k, EF_W), INTEGER_Number), (int32)getv(e, EMG(k, EF_H), INTEGER_Number),
			(int32)getv(e, EMG(k, EF_X), INTEGER_Number), (int32)getv(e, EMG(k, EF_Y), INTEGER_Number),
			m ? "," : "", m < 7 ? methodword[m] : "");
		if (pos + strlen(s) + 1 > bufsize) break;
		strcpy(buf + pos, s);
		arr[n++] = buf + pos;
		pos += strlen(s) + 1;
	}
	arr[n] = NULL;
}

/* Enable what the format and the check boxes allow. */
static void update_ghosting(Edit *e)
{
	BOOL emblem = getv(e, GID_FORMAT, CHOOSER_Selected) == 1;
	BOOL same = getv(e, GID_SEM_SAME, GA_Selected);
	for (int id = GID_IMG; id <= GID_SEM_EFF; id++)
	{
		BOOL off = !emblem;
		if (id >= GID_SEM && id <= GID_SEM_EFF) off = off || same;
		if (id == GID_EM || id == GID_EM_POP) off = off || getv(e, GID_EM_OWN, GA_Selected);
		if (id == GID_SEM || id == GID_SEM_POP) off = off || same || getv(e, GID_SEM_OWN, GA_Selected);
		if (getv(e, id, GA_Disabled) != (uint32)off)
		{
			setv(e, id, GA_Disabled, off);
			RefreshGList((struct Gadget *)e->g[id], e->window, NULL, 1);
		}
	}
}

/* "The selected image gets the same emblem": the selected emblem's (disabled) fields
 * show the emblem's values */
static void sync_same(Edit *e)
{
	if (!getv(e, GID_SEM_SAME, GA_Selected)) return;
	for (int k = EF_NAME; k <= EF_EFF; k++)
	{
		uint32 attr = k == EF_NAME ? STRINGA_TextVal : k == EF_OWN ? GA_Selected : k == EF_EFF ? CHOOSER_Selected : INTEGER_Number;
		uint32 v = getv(e, EMG(0, k), attr), old = getv(e, EMG(1, k), attr);
		if (k == EF_POP) continue;
		if (k == EF_NAME ? strcmp((STRPTR)v ? (STRPTR)v : "", (STRPTR)old ? (STRPTR)old : "") != 0 : v != old)
		{
			setv(e, EMG(1, k), attr, v);
			RefreshGList((struct Gadget *)e->g[EMG(1, k)], e->window, NULL, 1);
		}
	}
}

/* ---- the preview: the module composes it from a temporary icon ---- */

static void make_preview(Edit *e)
{
	char buf[2048];
	STRPTR arr[MAXEXTRA + 8];
	int32 err = 0;
	BOOL emblem = getv(e, GID_FORMAT, CHOOSER_Selected) == 1;
	struct DiskObject *p = NULL;

	sync_same(e);
	build_settings(e, buf, sizeof(buf), arr);
	if (PutIconTags(e->tmp, e->own,
		ICONPUTA_FileFormat, emblem ? (uint32)EMBLEM_FORMAT : ~0UL,
		ICONPUTA_NoFallback, TRUE,
		emblem ? EMBLEMA_SetSettings : TAG_IGNORE, (uint32)arr,
		ICONA_ErrorCode,     &err,
		TAG_DONE))
		p = GetIconTags(e->tmp,
			ICONGETA_FailIfUnavailable, TRUE,
			ICONGETA_Screen,            e->scr,
			TAG_DONE);
	if (e->preview) FreeDiskObject(e->preview);
	e->preview = p;
	for (int i = 0; i < 2; i++)
		RefreshGList((struct Gadget *)e->g[GID_PREV1 + i], e->window, NULL, 1);
}

static uint32 render_preview(struct Hook *hook, Object *space, struct gpRender *msg)
{
	Edit *e = hook->h_Data;
	int state = hook == &e->render[1] ? IDS_SELECTED : IDS_NORMAL;
	struct IBox box;
	struct Rectangle r;

	if (!e->preview || !msg->gpr_RPort) return 0;
	if (!GetAttr(SPACE_RenderBox, space, (uint32 *)&box))
		return 0;
	if (!GetIconRectangle(msg->gpr_RPort, e->preview, NULL, &r, ICONDRAWA_Borderless, TRUE, TAG_DONE))
		return 0;
	DrawIconState(msg->gpr_RPort, e->preview, NULL,
		box.Left + (box.Width - (r.MaxX - r.MinX + 1)) / 2 - r.MinX,
		box.Top + (box.Height - (r.MaxY - r.MinY + 1)) / 2 - r.MinY,
		state,
		ICONDRAWA_Borderless,      TRUE,
		ICONDRAWA_Frameless,       TRUE,
		ICONDRAWA_EraseBackground, FALSE,
		TAG_DONE);
	return 0;
}

/* ---- image files ---- */

/* full path of a drawer (resolves assigns), "" if it doesn't exist */
static void full_path(CONST_STRPTR name, char *out, size_t size)
{
	BPTR l = Lock(name, SHARED_LOCK);
	out[0] = 0;
	if (l)
	{
		if (!NameFromLock(l, out, size)) out[0] = 0;
		UnLock(l);
	}
}

static BOOL copy_file(CONST_STRPTR from, CONST_STRPTR to)
{
	BPTR in = Open(from, MODE_OLDFILE), out;
	char buf[8192];
	int32 n;
	BOOL ok = FALSE;
	if (!in) return FALSE;
	if ((out = Open(to, MODE_NEWFILE)))
	{
		ok = TRUE;
		while ((n = Read(in, buf, sizeof(buf))) > 0)
			if (Write(out, buf, n) != n) { ok = FALSE; break; }
		if (n < 0) ok = FALSE;
		if (!Close(out)) ok = FALSE;
		if (!ok) Delete(to);
	}
	Close(in);
	return ok;
}

/* The file requester for an image or emblem: the chosen file as a setting name
 * (relative to ENVARC:sys/emblem, without ".png") in the string gadget id. */
static void pick_image(Edit *e, int id, CONST_STRPTR title)
{
	struct FileRequester *fr;
	char dir[PATHLEN], file[PATHLEN], path[PATHLEN], name[PATHLEN];
	STRPTR cur = (STRPTR)getv(e, id, STRINGA_TextVal);

	/* start where the current one is */
	strlcpy(dir, EMBLEM_IMAGEDIR, sizeof(dir));
	file[0] = 0;
	if (cur && *cur)
	{
		strlcpy(path, EMBLEM_IMAGEDIR, sizeof(path));
		AddPart(path, cur, sizeof(path));
		strlcpy(file, FilePart(path), sizeof(file));
		*PathPart(path) = 0;
		strlcpy(dir, path, sizeof(dir));
		if (!strchr(file, '.')) strlcat(file, ".png", sizeof(file));
	}
	if (!(fr = AllocAslRequestTags(ASL_FileRequest, TAG_DONE))) return;
	if (AslRequestTags(fr,
		ASLFR_Window,         e->window,
		ASLFR_SleepWindow,    TRUE,
		ASLFR_TitleText,      title,
		ASLFR_InitialDrawer,  dir,
		ASLFR_InitialFile,    file,
		ASLFR_InitialPattern, "#?.png",
		ASLFR_DoPatterns,     TRUE,
		ASLFR_RejectIcons,    TRUE,
		TAG_DONE) && fr->fr_File[0])
	{
		char chosen[PATHLEN];
		size_t n = strlen(e->imgdir);
		full_path(fr->fr_Drawer, chosen, sizeof(chosen));
		if (n && Strnicmp(chosen, e->imgdir, n) == 0 && (chosen[n] == 0 || chosen[n] == '/'))
		{
			/* in ENVARC:sys/emblem or a drawer below it */
			strlcpy(name, chosen[n] == '/' ? chosen + n + 1 : "", sizeof(name));
			if (name[0]) strlcat(name, "/", sizeof(name));
			strlcat(name, fr->fr_File, sizeof(name));
		}
		else
		{
			char text[PATHLEN + 200], to[PATHLEN];
			int32 yes = 0;
			strlcpy(path, fr->fr_Drawer, sizeof(path));
			AddPart(path, fr->fr_File, sizeof(path));
			snprintf(text, sizeof(text), "Images must be in %s.\nCopy %s there?", EMBLEM_IMAGEDIR, fr->fr_File);
			request(e, text, "Copy|Cancel", &yes);
			name[0] = 0;
			if (yes)
			{
				strlcpy(to, EMBLEM_IMAGEDIR, sizeof(to));
				AddPart(to, fr->fr_File, sizeof(to));
				if (copy_file(path, to))
					strlcpy(name, fr->fr_File, sizeof(name));
				else
					request(e, "The image could not be copied.", "OK", NULL);
			}
		}
		n = strlen(name);
		if (n > 4 && Stricmp(name + n - 4, ".png") == 0) name[n - 4] = 0;
		if (name[0] && !es_valid_name(name, strlen(name)))
		{
			request(e, "That name is too long for a setting (63 characters).", "OK", NULL);
			name[0] = 0;
		}
		if (name[0])
		{
			setv(e, id, STRINGA_TextVal, (uint32)name);
			RefreshGList((struct Gadget *)e->g[id], e->window, NULL, 1);
		}
	}
	FreeAslRequest(fr);
}

/* ---- the window ---- */

static Object *label(CONST_STRPTR text)
{
	return LabelObject, LABEL_Text, text, LabelEnd;
}

static Object *name_row(Edit *e, int id, int pop, CONST_STRPTR initial)
{
	return HLayoutObject,
		LAYOUT_AddChild, e->g[id] = StringObject,
			GA_ID, id, GA_RelVerify, TRUE, GA_TabCycle, TRUE,
			STRINGA_MaxChars, ES_NAMELEN - 1,
			STRINGA_TextVal, initial,
			STRINGA_MinVisible, 18,
		StringEnd,
		LAYOUT_AddChild, e->g[pop] = ButtonObject,
			GA_ID, pop, GA_RelVerify, TRUE,
			BUTTON_AutoButton, BAG_POPFILE,
		ButtonEnd,
		CHILD_WeightedWidth, 0,
	LayoutEnd;
}

static Object *effect(Edit *e, int id, int m)
{
	return e->g[id] = ChooserObject,
		GA_ID, id, GA_RelVerify, TRUE,
		CHOOSER_LabelArray, effects,
		CHOOSER_Selected, m,
	ChooserEnd;
}

static Object *number(Edit *e, int id, int32 v, int32 min, int32 max)
{
	return e->g[id] = IntegerObject,
		GA_ID, id, GA_RelVerify, TRUE, GA_TabCycle, TRUE,
		INTEGER_Number, v, INTEGER_Minimum, min, INTEGER_Maximum, max,
		INTEGER_MaxChars, 5, INTEGER_Arrows, TRUE,
	IntegerEnd;
}

/* emblem i (0 normal, 1 selected): its picture ... */
static Object *emblem_name_row(Edit *e, int i, const ESEmblem *em)
{
	return HLayoutObject,
		LAYOUT_AddChild, name_row(e, EMG(i, EF_NAME), EMG(i, EF_POP), em->set && !em->internal ? em->name : ""),
		LAYOUT_AddChild, e->g[EMG(i, EF_OWN)] = CheckBoxObject,
			GA_ID, EMG(i, EF_OWN), GA_RelVerify, TRUE,
			GA_Text, "The icon's own picture",
			GA_Selected, em->set && em->internal,
		CheckBoxEnd,
		CHILD_WeightedWidth, 0,
	LayoutEnd;
}

/* ... and its size, position and effect */
static Object *emblem_size_row(Edit *e, int i, const ESEmblem *em)
{
	return HLayoutObject,
		LAYOUT_AddChild, number(e, EMG(i, EF_W), em->width, 0, 512),
		CHILD_WeightedWidth, 0,
		LAYOUT_AddChild, number(e, EMG(i, EF_H), em->height, 0, 512),
		CHILD_WeightedWidth, 0,
		CHILD_Label, label("x"),
		LAYOUT_AddChild, number(e, EMG(i, EF_X), em->x, -256, 256),
		CHILD_WeightedWidth, 0,
		CHILD_Label, label("  Position"),
		LAYOUT_AddChild, number(e, EMG(i, EF_Y), em->y, -256, 256),
		CHILD_WeightedWidth, 0,
		CHILD_Label, label(","),
		LAYOUT_AddChild, SpaceObject, SpaceEnd,
		LAYOUT_AddChild, effect(e, EMG(i, EF_EFF), em->method),
		CHILD_WeightedWidth, 0,
		CHILD_Label, label("Effect"),
	LayoutEnd;
}

/* default image i: name, file button, effect */
static Object *image_row(Edit *e, int i, const ESImage *im)
{
	return HLayoutObject,
		LAYOUT_AddChild, name_row(e, i ? GID_SIMG : GID_IMG, i ? GID_SIMG_POP : GID_IMG_POP, im->set ? im->name : ""),
		LAYOUT_AddChild, effect(e, i ? GID_SIMG_EFF : GID_IMG_EFF, im->method),
		CHILD_WeightedWidth, 0,
		CHILD_Label, label("Effect"),
	LayoutEnd;
}

static Object *make_window(Edit *e, const ESpec *sp, BOOL emblem, BOOL same)
{
	ESEmblem none;
	memset(&none, 0, sizeof(none));
	snprintf(e->title, sizeof(e->title), APPNAME ": %s", e->name);
	for (int i = 0; i < 2; i++)
	{
		e->render[i].h_Entry = (HOOKFUNC)render_preview;
		e->render[i].h_Data  = e;
	}
	return WindowObject,
		WA_Title,         e->title,
		WA_ScreenTitle,   VERS,
		WA_PubScreen,     e->scr,
		WA_Activate,      TRUE,
		WA_DepthGadget,   TRUE,
		WA_DragBar,       TRUE,
		WA_CloseGadget,   TRUE,
		WA_SizeGadget,    TRUE,
		WINDOW_Position,  WPOS_CENTERMOUSE,
		WINDOW_ParentGroup, VLayoutObject,
			LAYOUT_SpaceOuter, TRUE,
			LAYOUT_DeferLayout, TRUE,

			/* preview and format */
			LAYOUT_AddChild, HLayoutObject,
				LAYOUT_AddChild, HLayoutObject,
					LAYOUT_BevelStyle, BVS_GROUP,
					LAYOUT_Label, "Preview",
					LAYOUT_AddChild, e->g[GID_PREV1] = SpaceObject,
						GA_ID, GID_PREV1, GA_ReadOnly, TRUE,
						SPACE_MinWidth, 100, SPACE_MinHeight, 100,
						SPACE_RenderHook, &e->render[0],
					SpaceEnd,
					LAYOUT_AddChild, e->g[GID_PREV2] = SpaceObject,
						GA_ID, GID_PREV2, GA_ReadOnly, TRUE,
						SPACE_MinWidth, 100, SPACE_MinHeight, 100,
						SPACE_RenderHook, &e->render[1],
					SpaceEnd,
				LayoutEnd,
				CHILD_WeightedWidth, 0,
				LAYOUT_AddChild, VLayoutObject,
					LAYOUT_VertAlignment, LALIGN_CENTER,
					LAYOUT_AddChild, HLayoutObject,
						LAYOUT_AddChild, e->g[GID_FORMAT] = ChooserObject,
							GA_ID, GID_FORMAT, GA_RelVerify, TRUE,
							CHOOSER_LabelArray, formats,
							CHOOSER_Selected, emblem ? 1 : 0,
						ChooserEnd,
						CHILD_WeightedWidth, 0,
						CHILD_Label, label("Format"),
						LAYOUT_AddChild, SpaceObject, SpaceEnd,
					LayoutEnd,
					CHILD_WeightedHeight, 0,
				LayoutEnd,
			LayoutEnd,
			CHILD_WeightedHeight, 0,

			/* default images */
			LAYOUT_AddChild, VLayoutObject,
				LAYOUT_BevelStyle, BVS_GROUP,
				LAYOUT_Label, "Image",
				LAYOUT_AddChild, image_row(e, 0, &sp->image[0]),
				CHILD_Label, label("Normal"),
				LAYOUT_AddChild, image_row(e, 1, &sp->image[1]),
				CHILD_Label, label("Selected"),
			LayoutEnd,
			CHILD_WeightedHeight, 0,

			/* emblems */
			LAYOUT_AddChild, VLayoutObject,
				LAYOUT_BevelStyle, BVS_GROUP,
				LAYOUT_Label, "Emblem",
				LAYOUT_AddChild, emblem_name_row(e, 0, sp->emblem[0].set ? &sp->emblem[0] : &none),
				CHILD_Label, label("Normal"),
				LAYOUT_AddChild, emblem_size_row(e, 0, sp->emblem[0].set ? &sp->emblem[0] : &none),
				CHILD_Label, label("Size"),
				LAYOUT_AddChild, e->g[GID_SEM_SAME] = CheckBoxObject,
					GA_ID, GID_SEM_SAME, GA_RelVerify, TRUE,
					GA_Text, "The selected image gets the same emblem",
					GA_Selected, same,
				CheckBoxEnd,
				CHILD_Label, label(""),
				LAYOUT_AddChild, emblem_name_row(e, 1, sp->emblem[1].set ? &sp->emblem[1] : &none),
				CHILD_Label, label("Selected"),
				LAYOUT_AddChild, emblem_size_row(e, 1, sp->emblem[1].set ? &sp->emblem[1] : &none),
				CHILD_Label, label("Size"),
			LayoutEnd,
			CHILD_WeightedHeight, 0,

			LAYOUT_AddChild, HLayoutObject,
				LAYOUT_AddChild, e->g[GID_SAVE] = ButtonObject,
					GA_ID, GID_SAVE, GA_RelVerify, TRUE, GA_Text, "_Save",
				ButtonEnd,
				LAYOUT_AddChild, SpaceObject, SpaceEnd,
				LAYOUT_AddChild, e->g[GID_CANCEL] = ButtonObject,
					GA_ID, GID_CANCEL, GA_RelVerify, TRUE, GA_Text, "_Cancel",
				ButtonEnd,
			LayoutEnd,
			CHILD_WeightedHeight, 0,
		LayoutEnd,
	WindowEnd;
}

/* ---- load, save ---- */

static BOOL same_emblem(const ESEmblem *a, const ESEmblem *b)
{
	return a->set == b->set && a->internal == b->internal && a->method == b->method && a->width == b->width
		&& a->height == b->height && a->x == b->x && a->y == b->y && strcmp(a->name, b->name) == 0;
}

static int32 save(Edit *e)
{
	char buf[2048];
	STRPTR arr[MAXEXTRA + 8];
	int32 err = 0;
	BOOL emblem = getv(e, GID_FORMAT, CHOOSER_Selected) == 1;

	if (!emblem && !e->wasemblem) return 0;   /* a normal icon stays as it was */
	build_settings(e, buf, sizeof(buf), arr);
	if (!PutIconTags(e->name, e->own,
		ICONPUTA_FileFormat,      emblem ? (uint32)EMBLEM_FORMAT : ~0UL,
		ICONPUTA_NoFallback,      TRUE,
		ICONPUTA_NotifyWorkbench, TRUE,
		emblem ? EMBLEMA_SetSettings : TAG_IGNORE, (uint32)arr,
		ICONA_ErrorCode,          &err,
		TAG_DONE))
		return err ? err : IoErr() ? IoErr() : ERROR_OBJECT_WRONG_TYPE;
	return 0;
}

/* returns FALSE if the icon could not be edited (message shown) */
static BOOL edit_icon(CONST_STRPTR arg, struct Screen *scr)
{
	Edit *e;
	STRPTR fmt = NULL, *es = NULL;
	int32 err = 0;
	char text[PATHLEN + 128];
	ESpec spec;
	BOOL ok = TRUE;

	if (!(e = AllocVecTags(sizeof(*e), AVT_ClearWithValue, 0, TAG_DONE))) return FALSE;
	strlcpy(e->name, arg, sizeof(e->name));
	{
		size_t n = strlen(e->name);
		if (n > 5 && Stricmp(e->name + n - 5, ".info") == 0) e->name[n - 5] = 0;
	}
	e->scr = scr;
	snprintf(e->tmp, sizeof(e->tmp), "T:" APPNAME ".%lx", (uint32)FindTask(NULL));
	full_path(EMBLEM_IMAGEDIR, e->imgdir, sizeof(e->imgdir));

	e->own = GetIconTags(e->name,
		ICONGETA_FailIfUnavailable,  TRUE,
		ICONGETA_RemapIcon,          FALSE,
		ICONGETA_GenerateImageMasks, FALSE,
		ICONGETA_FileFormat,         &fmt,
		ICONA_ErrorCode,             &err,
		EMBLEMA_NoCompose,           TRUE,
		EMBLEMA_GetSettings,         &es,
		TAG_DONE);
	if (!e->own)
	{
		char msg[100];
		Fault(err ? err : ERROR_OBJECT_NOT_FOUND, NULL, msg, sizeof(msg));
		snprintf(text, sizeof(text), "%s.info:\n%s", e->name, msg);
		request(NULL, text, "OK", NULL);
		FreeVec(e);
		return FALSE;
	}
	e->wasemblem = fmt && Stricmp(fmt, EMBLEM_FORMAT) == 0;

	/* the settings: the four keys into the fields, others kept as they are */
	{
		char packed[2048];
		size_t pos = 0;
		for (STRPTR *s = es; s && *s; s++)
		{
			size_t l = strlen(*s) + 1;
			if (has_key(*s))
			{
				if (pos + l <= sizeof(packed)) { memcpy(packed + pos, *s, l); pos += l; }
			}
			else if (e->nextra < MAXEXTRA)
			{
				if ((e->extra[e->nextra] = AllocVecTags(l, TAG_DONE))) memcpy(e->extra[e->nextra++], *s, l);
			}
		}
		es_parse(packed, pos, &spec);
	}
	if (!(e->win = make_window(e, &spec, e->wasemblem,
		!spec.emblem[1].set ? !spec.emblem[0].set : same_emblem(&spec.emblem[0], &spec.emblem[1]))))
	{
		request(NULL, "The window could not be made (ReAction classes missing?).", "OK", NULL);
		ok = FALSE;
	}
	else if (!(e->window = RA_OpenWindow(e->win)))
	{
		request(NULL, "The window could not be opened.", "OK", NULL);
		ok = FALSE;
	}
	else
	{
		uint32 sig = 0, result;
		uint16 code;
		BOOL done = FALSE;
		GetAttr(WINDOW_SigMask, e->win, &sig);
		update_ghosting(e);
		make_preview(e);
		while (!done)
		{
			uint32 got = Wait(sig | SIGBREAKF_CTRL_C);
			if (got & SIGBREAKF_CTRL_C) break;
			while ((result = RA_HandleInput(e->win, &code)) != WMHI_LASTMSG)
			{
				switch (result & WMHI_CLASSMASK)
				{
					case WMHI_CLOSEWINDOW:
						done = TRUE;
						break;
					case WMHI_GADGETUP:
					{
						int id = result & WMHI_GADGETMASK;
						switch (id)
						{
							case GID_SAVE:
								if ((err = save(e)))
								{
									char msg[100];
									Fault(err, NULL, msg, sizeof(msg));
									snprintf(text, sizeof(text), "%s.info was not saved:\n%s", e->name, msg);
									request(e, text, "OK", NULL);
								}
								else
									done = TRUE;
								break;
							case GID_CANCEL:
								done = TRUE;
								break;
							case GID_FORMAT:
								if (code == 0 && e->wasemblem)
								{
									int32 yes = 0;
									request(e, "A normal icon can't keep the Emblem settings:\n"
										"they are removed when you save.", "Normal icon|Cancel", &yes);
									if (!yes)
									{
										setv(e, GID_FORMAT, CHOOSER_Selected, 1);
										RefreshGList((struct Gadget *)e->g[GID_FORMAT], e->window, NULL, 1);
									}
								}
								update_ghosting(e);
								make_preview(e);
								break;
							case GID_IMG_POP:  pick_image(e, GID_IMG, "Image");           make_preview(e); break;
							case GID_SIMG_POP: pick_image(e, GID_SIMG, "Selected image"); make_preview(e); break;
							case GID_EM_POP:   pick_image(e, GID_EM, "Emblem");           make_preview(e); break;
							case GID_SEM_POP:  pick_image(e, GID_SEM, "Selected emblem"); make_preview(e); break;
							case GID_EM_OWN: case GID_SEM_OWN: case GID_SEM_SAME:
								update_ghosting(e);
								make_preview(e);
								break;
							default:
								make_preview(e);
								break;
						}
						break;
					}
				}
			}
		}
	}
	if (e->win) DisposeObject(e->win);
	if (e->preview) FreeDiskObject(e->preview);
	FreeDiskObject(e->own);
	DeleteDiskObject(e->tmp);
	for (int i = 0; i < e->nextra; i++) FreeVec(e->extra[i]);
	FreeVec(e);
	return ok;
}

/* ---- start ---- */

static BOOL ask_icon(struct Screen *scr, char *out, size_t size)
{
	struct FileRequester *fr = AllocAslRequestTags(ASL_FileRequest, TAG_DONE);
	BOOL ok = FALSE;
	if (!fr) return FALSE;
	if (AslRequestTags(fr,
		ASLFR_Screen,         scr,
		ASLFR_TitleText,      APPNAME ": choose an icon",
		ASLFR_InitialPattern, "#?.info",
		ASLFR_DoPatterns,     TRUE,
		TAG_DONE) && fr->fr_File[0])
	{
		strlcpy(out, fr->fr_Drawer, size);
		AddPart(out, fr->fr_File, size);
		ok = TRUE;
	}
	FreeAslRequest(fr);
	return ok;
}

int main(int argc, char **argv)
{
	struct Screen *scr = NULL;
	char path[PATHLEN];
	int rc = 0, n = 0;

	if (argc == 0)
	{
		/* Workbench: the icons that were selected with EmblemInfo */
		struct WBStartup *wb = (struct WBStartup *)argv;
		scr = LockPubScreen(NULL);
		for (int i = 1; i < wb->sm_NumArgs; i++)
		{
			struct WBArg *a = &wb->sm_ArgList[i];
			if (!NameFromLock(a->wa_Lock, path, sizeof(path))) continue;
			if (a->wa_Name && a->wa_Name[0]) AddPart(path, a->wa_Name, sizeof(path));
			else AddPart(path, "Disk", sizeof(path));      /* a disk: its icon is Disk.info */
			edit_icon(path, scr);
			n++;
		}
		if (!n && ask_icon(scr, path, sizeof(path))) edit_icon(path, scr);
	}
	else
	{
		int32 args[2] = { 0, 0 };
		struct RDArgs *rda = ReadArgs("FILES/M,PUBSCREEN/K", args, NULL);
		if (!rda)
		{
			PrintFault(IoErr(), APPNAME);
			return 20;
		}
		scr = LockPubScreen((STRPTR)args[1]);
		if (!scr)
		{
			Printf(APPNAME ": no public screen %s\n", (STRPTR)args[1]);
			FreeArgs(rda);
			return 20;
		}
		for (STRPTR *f = (STRPTR *)args[0]; f && *f; f++, n++)
			if (!edit_icon(*f, scr)) rc = 10;
		if (!n && ask_icon(scr, path, sizeof(path)) && !edit_icon(path, scr)) rc = 10;
		FreeArgs(rda);
	}
	if (scr) UnlockPubScreen(NULL, scr);
	return rc;
}
