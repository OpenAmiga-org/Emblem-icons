/*
 * emblemprefs.h - the global settings file (EMBLEM_PREFS, src/emblem.h),
 * portable C. A text file of KEY=VALUE lines; keys are case-insensitive,
 * lines starting with '#' or ';' are comments, unknown keys and bad values
 * are ignored (the setting keeps its default):
 *
 *   METHOD=SHADOW          method for settings without one (images and emblems)
 *   IMAGEMETHOD=NONE       ... only for IMAGE=/IMAGESELECTED= (wins over METHOD)
 *   EMBLEMMETHOD=SHADOW    ... only for EMBLEM=/EMBLEMSELECTED= (wins over METHOD)
 *   SHADOWOFFSET=5,5       -16..16 (one number = both)
 *   SHADOWBLUR=2           0..8
 *   SHADOWOPACITY=50       percent
 *   GLOWSIZE=2             1..8
 *   GLOWOPACITY=80         percent
 *   GLOWCOLOR=FFFFFF       RGB in hex ('#', '$' or '0x' in front allowed)
 */
#ifndef EMBLEMPREFS_H
#define EMBLEMPREFS_H

#include "compose.h"

#define EP_MAXFILE 4096

/* Built-in settings: methods NONE, shadow +5,+5 blur 2 at 50 %, white glow of 2 at 80 %. */
void ep_defaults(CPPrefs *p);

/* Apply the settings in text to p. Returns the number of settings taken. */
int ep_parse(const char *text, uint32_t len, CPPrefs *p);

#endif
