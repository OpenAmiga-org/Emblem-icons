# Emblem

AmigaOS 4 icon module (`emblem.iconmodule`) for openamiga.org project 34 "Emblem icon plugin": icons
with default images and emblems, composed when icon.library loads them. Plan and step results:
[docs/plan.md](docs/plan.md), file format: [docs/format.md](docs/format.md), user manual:
[package/Emblem/Emblem.guide](package/Emblem/Emblem.guide).

Status: all six steps of the plan done. The module loads and saves the Emblem format and composes
`IMAGE=` / `IMAGESELECTED=` default images and `EMBLEM=` / `EMBLEMSELECTED=` emblems from
`ENVARC:sys/emblem/` with the methods NONE, DARK, BRIGHT, GRAY, SHADOW and GLOW; settings without
a method use the global ones in `ENV:sys/emblem.prefs` (keys in src/emblemprefs.h). Since 1.1 these
four settings are kept in the icon file (the `ESET` chunk), not in the tool types: most OS 4 Prefs
editors read all of their tool types as arguments and refused to start with them. The release package
`dist/emblem_icons.lha` has a small sample set (AmigaOS 4.1 icon style) for its ten example
icons, RemoveSamples (deletes just the sample images), the guide and an Install script that installs,
updates and removes everything.

Public domain ([UNLICENSE](UNLICENSE)), the art too.

Download: the package is on the [releases page](https://github.com/orgin/emblemicon/releases) (1.0: `Emblem.lha`; from 1.1 on: `emblem_icons.lha`, and the Glenz icon set as `emblem_icons_glenz.lha`). Unpack it on AmigaOS 4.1 and double-click Install, then restart.

## Layout

| Path | What |
|---|---|
| `src/emblemfile.[ch]` | Emblem file format codec, portable C (module, host tools and tests) |
| `src/module.c` | emblem.iconmodule (icon.library loader/saver module) |
| `src/png.[ch]` | PNG decoder to ARGB, portable |
| `src/emblemspec.[ch]` | the IMAGE/IMAGESELECTED/EMBLEM/EMBLEMSELECTED settings, portable |
| `src/compose.[ch]` | the composition engine (scaling, compositing, methods), integer only, portable |
| `src/emblemprefs.[ch]` | the settings file (emblem.prefs), portable |
| `src/imagecache.[ch]` | decoded default images and emblems by name, and the settings (module only) |
| `src/emblem.h` | public: format name, image folder, the `EMBLEMA_NoCompose`, `EMBLEMA_GetSettings` and `EMBLEMA_SetSettings` tags |
| `src/emblemicon.c` | EmblemIcon: convert icons to/from the Emblem format (patterns, ALL), show them, set/remove settings and tool types (SET, UNSET, TYPE) |
| `art/` | the sample art set of the package; `art/package/` the pictures of the package's own icons |
| `package/` | Install script, guide, readme, examples ReadMe, the package's native icons |
| `tools/make_art.py` | reads the art set and the package icons' pictures (made in the OS 4.1 style elsewhere), draws the extra emblems, writes the `.argb` files for mkicon |
| `tools/mkemblem.c` | host tool: writes Emblem icons (`make tools`) |
| `tools/make_examples.py` | the package's example icons (and a render sheet of them) |
| `tools/make_lha.sh` | puts the release together: `dist/emblem_icons.lha` + `dist/emblem_icons.readme` (`OUT=` and `RELEASES=/nonexistent` for test builds; the readme goes next to `OUT`) |
| `tools/iconset_build.py` | the Glenz icon set: mapping check, export, its own archive `dist/emblem_icons_glenz.lha` (package/iconset/README.md) |
| `tools/os4/mkicon.c` | guest helper that saves the package's native icons (package/icons/README.md) |
| `tools/render_sheet.py` | render sheets of composed icons (`step3`, `step4` or a JSON case list) |
| `tests/host/` | host tests: format codec, PNG decoder (PngSuite vs pypng), settings parser, engine |
| `tests/host/render.c` | host renderer (`build/host/render`): the module's composition on the host |
| `tests/os4/run_os4.py` | guest test runner (MCPd, target os4-amigaone), steps 1-6 |
| `tests/os4/run_iconset.py` | guest test of the icon set's installer: install, update, Restore, install again, Remove |
| `tests/os4/run_prefs.py` | guest test: with the icon set installed, every Prefs editor in SYS:Prefs starts from Workbench |
| `tests/os4/icontest.c` | guest helper: dump, make test icons, edit/snapshot/dup/layout+save |
| `tests/os4/make_test_pngs.py`, `make_bad_files.py`, `memeater.c` | test images, broken files, low memory |
| `docs/art/` | the test art of steps 3-5 (not the package's) |
| `tests/samples/pngsuite/` | PngSuite by Willem van Schaik (free to use, see its LICENSE) |
| `spike/` | the feasibility spike (logging module, iconload) |

## Build, test, release

```
make test                       # host tests with ASan/UBSan (needs zlib; pypng in ~/build/emblem-venv)
make os4                        # cross-build in the walkero docker -> build/os4/
make tools                      # host tool mkemblem (example icons)
make os4-profile                # module that prints load phase times to the debug buffer (testing only)
tests/os4/run_os4.py --deploy   # install the module in the guest, reboot it, run the guest tests 1-5
tests/os4/run_os4.py --step=2   # only one step's guest tests (repeat --step= for more)
tests/os4/run_os4.py --step=5 --only=mem,speed   # some step 5 sections
tools/make_lha.sh               # dist/emblem_icons.lha (needs make os4 tools; checks the History entries)
tests/os4/run_os4.py --step=6   # the package: install, update, examples, remove (alone; resets the guest)
tools/make_art.py art --preview docs/step6_art.png   # the art sheet + the icons' .argb files (then mkicon, rebuild the package)
```

## Use (guest)

Install the package (Install script), or by hand:

```
Copy emblem.iconmodule LIBS:IconModules/     ; then reboot: icon.library opens modules at startup
EmblemIcon SYS:Devs                          ; show format, tool types and settings
EmblemIcon SYS:Devs TO=EMBLEM                ; convert to the Emblem format
EmblemIcon SYS:Devs TO=AMIGA                 ; back to a native icon (without the settings)
EmblemIcon Work: ALL                         ; list the Emblem icons in Work: and below
EmblemIcon Work:Music SET="IMAGE=DrawerNS|IMAGESELECTED=DrawerS|EMBLEM=EmblemMusic,28,28,34,32"
                                             ; Emblem icon with these settings
EmblemIcon Work: ALL TYPE=DRAWER SET="IMAGE=DrawerNS|EMBLEM=INTERNAL,30,30,33,30"
                                             ; every drawer: Emblem, with these settings
```

The PNGs go in `ENVARC:sys/emblem/`. Programs read and change an icon's settings with
`EMBLEMA_GetSettings` (GetIconTags) and `EMBLEMA_SetSettings` (PutIconTags); programs that need the
icon's own images pass `EMBLEMA_NoCompose, TRUE` to GetIconTags() (src/emblem.h).

Needs AmigaOS 4.1: icon.library with module support (V51.15+) and z.library 53+.
