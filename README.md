# Emblem-icons

Emblem is an icon module for AmigaOS 4 (`emblem.iconmodule`): an icon
borrows a shared default image (a drawer, a page) and gets an emblem on
it, composed when icon.library loads the icon. Emblem is an
[OpenAmiga.org project](http://openamiga.org/?function=gitproject&name=Emblem-icons).

Four settings, kept in the icon file (the `ESET` chunk, not the tool
types), say which images to use: `IMAGE=` / `IMAGESELECTED=` default
images and `EMBLEM=` / `EMBLEMSELECTED=` emblems from
`ENVARC:sys/emblem/`, with the effects `NONE`, `DARK`, `BRIGHT`, `GRAY`,
`SHADOW` and `GLOW`. Settings without an effect use the global ones in
`ENV:sys/emblem.prefs`. The repository also holds the Glenz icon set,
a full set of glass icons for the system built on Emblem.

Built on icon.library with module support (V51.15+) and z.library 53+.

Download: not on OS4Depot yet; the packages are on the
[GitHub releases page](https://github.com/OpenAmiga-org/Emblem-icons/releases)
(1.0: `Emblem.lha`; from 1.1 on: `emblem_icons.lha` with the module,
EmblemIcon, the guide, a small sample set and ten example icons, and the
Glenz icon set as `emblem_icons_glenz.lha`).

## Layout

- `src/module.c`: emblem.iconmodule (icon.library loader/saver module)
- `src/emblemfile.[ch]`: the Emblem file format codec, portable C (module,
  host tools and tests)
- `src/png.[ch]`: PNG decoder to ARGB, portable
- `src/emblemspec.[ch]`: the `IMAGE`/`IMAGESELECTED`/`EMBLEM`/
  `EMBLEMSELECTED` settings, portable
- `src/compose.[ch]`: the composition engine (scaling, compositing,
  effects), integer only, portable
- `src/emblemprefs.[ch]`: the settings file (`emblem.prefs`), portable
- `src/imagecache.[ch]`: decoded default images and emblems by name, and
  the settings (module only)
- `src/emblem.h`: public: format name, image folder, the
  `EMBLEMA_NoCompose`, `EMBLEMA_GetSettings` and `EMBLEMA_SetSettings`
  tags
- `src/emblemicon.c`: EmblemIcon: converts icons to and from the Emblem
  format (patterns, ALL), shows them, sets and removes settings and tool
  types (SET, UNSET, TYPE)
- `src/embleminfo.c`: EmblemInfo, a ReAction editor for an icon's Emblem
  settings (not in the package yet)
- `art/`: the package's sample images; `art/package/` the pictures of
  the package's own icons
- `package/`: Install script, guide, OS4Depot readme, examples ReadMe,
  the package's native icons; `package/iconset/`: the Glenz set's
  installer and readme
- `docs/`: `plan.md` (plan and step results), `format.md` (the file
  format), `embleminfo.md`, `iconset_plan.md` and `iconset_mapping.md`
  (the Glenz set), `iconsets/` (the set's review sheets)
- `tools/make_art.py`: reads the sample images and the package icons'
  pictures, draws the extra emblems, writes the `.argb` files for mkicon
- `tools/mkemblem.c`: host tool that writes Emblem icons (`make tools`)
- `tools/make_examples.py`: the package's example icons (and a render
  sheet of them)
- `tools/make_lha.sh`: puts the release together: `dist/emblem_icons.lha`
  and `dist/emblem_icons.readme`
- `tools/update_readme.py`: the Changelog below, from the readme
- `tools/iconset_build.py`: the Glenz set: mapping check, export, its own
  archive `dist/emblem_icons_glenz.lha` (`package/iconset/README.md`);
  `tools/blender/` and `tools/glass_*.py`: how its pictures are made
- `tools/os4/mkicon.c`: guest helper that saves the package's native
  icons (`package/icons/README.md`)
- `tools/render_sheet.py`: render sheets of composed icons
- `tests/host/`: host tests: format codec, PNG decoder (PngSuite against
  pypng), settings parser, engine; `render.c`: the module's composition
  on the host (`build/host/render`)
- `tests/os4/`: guest tests (MCPd): `run_os4.py` (steps 1-6),
  `run_iconset.py` (the set's installer), `run_prefs.py` (every Prefs
  editor starts with the set installed), `run_wbinfo.py` (the Workbench
  Information window and Emblem icons), `icontest.c` (guest helper),
  test images, broken files, low memory
- `tests/samples/pngsuite/`: PngSuite by Willem van Schaik
- `spike/`: the feasibility spike (logging module, iconload)

## Using it

Install the package (its Install script), or by hand:

    Copy emblem.iconmodule LIBS:IconModules/  ; then reboot: icon.library
                                              ; opens modules at startup
    EmblemIcon SYS:Devs                       ; format, tool types, settings
    EmblemIcon SYS:Devs TO=EMBLEM             ; convert to the Emblem format
    EmblemIcon SYS:Devs TO=AMIGA              ; back to a native icon
    EmblemIcon Work: ALL                      ; list the Emblem icons
    EmblemIcon Work:Music SET="IMAGE=DrawerNS|IMAGESELECTED=DrawerS|EMBLEM=EmblemMusic,28,28,34,32"
    EmblemIcon Work: ALL TYPE=DRAWER SET="IMAGE=DrawerNS|EMBLEM=INTERNAL,30,30,33,30"

The PNGs go in `ENVARC:sys/emblem/`. The manual is
`package/Emblem/Emblem.guide`.

Programs read and change an icon's settings with `EMBLEMA_GetSettings`
(GetIconTags) and `EMBLEMA_SetSettings` (PutIconTags); programs that need
the icon's own images pass `EMBLEMA_NoCompose, TRUE` to GetIconTags()
(`src/emblem.h`).

## Building

    make test                  # host tests with ASan/UBSan (needs zlib;
                               # pypng in ~/build/emblem-venv)
    make os4                   # cross-build -> build/os4/
    make tools                 # host tool mkemblem (example icons)
    make os4-profile           # module that prints load times (testing)
    tests/os4/run_os4.py --deploy    # install in the guest, guest tests 1-5
    tests/os4/run_os4.py --step=2    # one step's guest tests
    tools/make_lha.sh          # dist/emblem_icons.lha (needs make os4 tools;
                               # checks the History entries)
    tests/os4/run_os4.py --step=6    # the package: install, update,
                               # examples, remove (resets the guest)
    tools/make_art.py art --preview docs/step6_art.png
                               # art sheet + the icons' .argb files
    tools/iconset_build.py package   # dist/emblem_icons_glenz.lha

The OS4 build needs the cross-compiler image
`walkero/amigagccondocker:os4-gcc15-3.6.1` (GCC 15, SDK 54.25).

## Design notes

- Icon modules (`LIBS:IconModules`, opened only when icon.library
  starts) are asked only about icon files icon.library can't read itself,
  so Emblem icons have their own format: IFF `FORM EMBL` (see
  `docs/format.md`). `EmblemIcon` converts icons to it and back.
- The icon's own images stay in the file; the module composes the
  default image and the emblem when the icon is loaded and never saves
  the composed picture. When a program changes only one of the two
  images, the other is written from the file's own image.
- Since 1.1 the four settings are in the `ESET` chunk instead of the
  tool types: most OS 4 Prefs editors read all of their tool types as
  arguments and refused to start with them.
- The composition engine is integer only and shared by the module and
  the host renderer, so the guest tests compare the module's pixels with
  host renders exactly.

## Changelog

<!-- changelog start: made by tools/update_readme.py from package/Emblem.readme -->
- **1.1** (2026-11-20): The settings are kept in the icon file, no longer in the tool types (most Prefs editors refused to start with them); module 1.1, EmblemIcon 1.2 (SET, UNSET, TYPE); small sample set and RemoveSamples; new AmigaOS 4.1 style pictures for the package's icons and the sample set.
- **1.0** (2026-11-15): First release.
<!-- changelog end -->

## History

Emblem started in 2008 as OpenAmiga.org project 34 "Emblem icon plugin"
in the OpenAmiga.org Subversion repository (a specification and code
examples). It was written anew in November 2026 and released as 1.0 on
GitHub. It started on GitHub as orgin/emblemicon and moved to the
OpenAmiga.org organization in November 2026 with its full commit
history; Subversion project 34 has a copy of the source since then.

Public domain, see `UNLICENSE` (The Unlicense), the art too. PngSuite in
`tests/samples/pngsuite` is by Willem van Schaik (free to use, see its
`LICENSE`).
