# EmblemInfo (design, 2026-11-17)

User's request (2026-11-16/17): not a copy of the Information window (it has far too many functions to
re-implement); instead a separate program, **EmblemInfo**, for what the new icon type needs:

- a preview of the icon,
- file requesters for the default image and the emblem,
- input fields for the emblem's position and size,
- a choice to use the icon's own picture as the emblem (`INTERNAL`),
- turning a normal icon into an Emblem icon, and an Emblem icon back into a normal one.

Everything else stays with Workbench's Information window, which works with Emblem icons (tested:
`tests/os4/run_wbinfo.py`).

## Starting it

- Workbench: select one or more icons, then shift-double-click EmblemInfo (or drop icons on its
  window); without icons it asks for one with a file requester.
- Shell: `EmblemInfo FILES/M [PUBSCREEN=name]` (with or without ".info").
- One window per icon.

## The window (ReAction)

```
+- EmblemInfo: Work:Music ----------------------------------------------------+
|  +---------+ +---------+   Format: [ Emblem icon        v]                   |
|  | normal  | |selected |   (Normal icon / Emblem icon; saved with Save)      |
|  | preview | | preview |                                                     |
|  +---------+ +---------+                                                     |
| - Image ------------------------------------------------------------------- |
|   Image:          [DrawerNS            ][file]  Effect: [Settings file v]    |
|   Selected image: [DrawerS             ][file]  Effect: [Settings file v]    |
| - Emblem ------------------------------------------------------------------ |
|   Emblem:         [EmblemMusic         ][file]  [ ] The icon's own picture   |
|                   Size [28] x [28]   Position [34] , [32]   Effect: [ v]     |
|   Selected emblem: [x] Same as the emblem                                    |
|                   [EmblemMusic         ][file]  [ ] The icon's own picture   |
|                   Size [28] x [28]   Position [34] , [32]   Effect: [ v]     |
|                                                                              |
| [Save]                                                            [Cancel]   |
+------------------------------------------------------------------------------+
```

- **Preview:** the icon as Workbench will show it, normal and selected, with the edited settings. It is
  made by the module itself: the icon (its own images, `EMBLEMA_NoCompose`) is saved to a temporary
  file in T: with the edited settings (`EMBLEMA_SetSettings`) and loaded again, so the preview is exact
  (methods, shadow, glow, the global settings).
- **File requesters** open in ENVARC:sys/emblem and accept PNG files; the setting gets the name without
  ".png" (sub-drawers kept: "glass/p_printer"). A file outside ENVARC:sys/emblem is copied there
  (asked first), since settings name images relative to that drawer.
- **Effect:** "Settings file" (no method: emblem.prefs decides), None, Shadow, Glow, Gray, Dark, Bright.
- **Size 0 x 0** = the emblem's own size (as in the settings).
- **Format:** a normal icon gets the Emblem fields when switched to "Emblem icon"; switching an Emblem icon
  to "Normal icon" asks first (its settings can't stay in a normal icon) and disables the fields.
- Fields that are empty leave that setting out (no IMAGE= = the icon's own picture).
- **Save** writes the icon (`PutIconTags` with `ICONPUTA_FileFormat` and `EMBLEMA_SetSettings`), keeping
  everything else (tool types, position, own images); **Cancel** closes without a change.

## Later (not in the first version)

- Catalogs (English built in first), an AppMenu item in Workbench's Tools menu, several icons at once.
