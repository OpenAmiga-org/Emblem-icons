/*
 * emblem.h - public definitions of emblem.iconmodule for programs.
 */
#ifndef EMBLEM_EMBLEM_H
#define EMBLEM_EMBLEM_H

#include <utility/tagitem.h>

/* Name of the module's icon file format (ICONPUTA_FileFormat, ICONGETA_FileFormat). */
#define EMBLEM_FORMAT    "Emblem"

/* Where IMAGE=, IMAGESELECTED=, EMBLEM= and EMBLEMSELECTED= names are looked up
 * ("Name" means EMBLEM_IMAGEDIR "Name.png"). */
#define EMBLEM_IMAGEDIR  "ENVARC:sys/emblem/"

/* Global settings (methods for tool types without one, shadow and glow), see
 * src/emblemprefs.h. ENV: first, then ENVARC:. */
#define EMBLEM_PREFS     "ENV:sys/emblem.prefs"
#define EMBLEM_PREFSARC  "ENVARC:sys/emblem.prefs"

/* Extra tags for icon.library's GetIconTagList(); icon.library passes them on to
 * the module (other loaders ignore them). */
#define EMBLEMA_Dummy     (TAG_USER + 0x454D0000)

/* BOOL: load the icon's own images, without default images or emblems
 * (what a program needs to edit the icon's own pictures or convert the icon). */
#define EMBLEMA_NoCompose (EMBLEMA_Dummy + 1)

#endif
