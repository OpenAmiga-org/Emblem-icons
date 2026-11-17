/*
 * emblem.h - public definitions of emblem.iconmodule for programs.
 */
#ifndef EMBLEM_EMBLEM_H
#define EMBLEM_EMBLEM_H

#include <utility/tagitem.h>

/* Name of the module's icon file format (ICONPUTA_FileFormat, ICONGETA_FileFormat). */
#define EMBLEM_FORMAT    "Emblem"

/* Where the names of the IMAGE=, IMAGESELECTED=, EMBLEM= and EMBLEMSELECTED=
 * settings are looked up ("Name" means EMBLEM_IMAGEDIR "Name.png"). */
#define EMBLEM_IMAGEDIR  "ENVARC:sys/emblem/"

/* Global settings (methods for settings without one, shadow and glow), see
 * src/emblemprefs.h. ENV: first, then ENVARC:. */
#define EMBLEM_PREFS     "ENV:sys/emblem.prefs"
#define EMBLEM_PREFSARC  "ENVARC:sys/emblem.prefs"

/* Extra tags for icon.library's GetIconTagList(); icon.library passes them on to
 * the module (other loaders ignore them). */
#define EMBLEMA_Dummy     (TAG_USER + 0x454D0000)

/* BOOL: load the icon's own images, without default images or emblems
 * (what a program needs to edit the icon's own pictures or convert the icon). */
#define EMBLEMA_NoCompose (EMBLEMA_Dummy + 1)

/* An Emblem icon's own settings (IMAGE=Name[,Method], IMAGESELECTED=...,
 * EMBLEM=Name[,W,H,X,Y,Method], EMBLEMSELECTED=...) are kept in the icon file
 * (the ESET chunk), not in its tool types: programs that read all of their
 * tool types as arguments never see them.
 *
 * EMBLEMA_GetSettings (STRPTR **), for GetIconTagList(): receives the
 * settings as a NULL-terminated array of "KEY=value" strings, or NULL when
 * the icon has none. Freed with the icon (FreeDiskObject()); read-only.
 * Not touched for icons of other formats: set the pointer to NULL first.
 *
 * EMBLEMA_SetSettings (STRPTR *), for PutIconTagList(): the settings the
 * Emblem file gets, a NULL-terminated array (NULL or empty = none) in place
 * of the ones the icon was loaded with. Without this tag an Emblem icon keeps
 * its settings when it is saved again (also after DupDiskObject()). Only the
 * file changes, not the DiskObject's images; other formats ignore the tag. */
#define EMBLEMA_GetSettings (EMBLEMA_Dummy + 2)
#define EMBLEMA_SetSettings (EMBLEMA_Dummy + 3)

#endif
