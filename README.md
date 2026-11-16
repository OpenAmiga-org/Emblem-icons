# Emblem

AmigaOS 4 icon module (`emblem.iconmodule`) for openamiga.org project 34 "Emblem icon plugin": icons
with default images and emblems, composed when icon.library loads them. Plan and step results:
[docs/plan.md](docs/plan.md), file format: [docs/format.md](docs/format.md), user manual:
[package/Emblem/Emblem.guide](package/Emblem/Emblem.guide).

Status: all six steps of the plan done. The module loads and saves the Emblem format and composes
`IMAGE=` / `IMAGESELECTED=` default images and `EMBLEM=` / `EMBLEMSELECTED=` emblems from
`ENVARC:sys/emblem/` with the methods NONE, DARK, BRIGHT, GRAY, SHADOW and GLOW; tool types without
a method use the settings in `ENV:sys/emblem.prefs` (keys in src/emblemprefs.h). The release package
`dist/Emblem.lha` has a small sample set (placeholder art, drawn by a script) for its ten example
icons, RemoveSamples (deletes just the sample images), the guide and an Install script that installs,
updates and removes everything.

Public domain ([UNLICENSE](UNLICENSE)), the art too.

Download: the package `Emblem.lha` is on the [releases page](https://github.com/orgin/emblemicon/releases). Unpack it on AmigaOS 4.1 and double-click Install, then restart.

## Layout

| Path | What |
|---|---|
| `src/emblemfile.[ch]` | Emblem file format codec, portable C (module, host tools and tests) |
| `src/module.c` | emblem.iconmodule (icon.library loader/saver module) |
| `src/png.[ch]` | PNG decoder to ARGB, portable |
| `src/emblemspec.[ch]` | the IMAGE/IMAGESELECTED/EMBLEM/EMBLEMSELECTED tool types, portable |
| `src/compose.[ch]` | the composition engine (scaling, compositing, methods), integer only, portable |
| `src/emblemprefs.[ch]` | the settings file (emblem.prefs), portable |
| `src/imagecache.[ch]` | decoded default images and emblems by name, and the settings (module only) |
| `src/emblem.h` | public: format name, image folder, `EMBLEMA_NoCompose` tag |
| `src/emblemicon.c` | EmblemIcon: convert icons to/from the Emblem format (patterns, ALL), show them, set/remove tool types (SET, UNSET, TYPE) |
| `art/` | the sample art set of the package (drawn by `tools/make_art.py`) |
| `package/` | Install script, guide, readme, examples ReadMe, the package's native icons |
| `tools/make_art.py` | draws the art set, the example's own picture and the package icons' pictures |
| `tools/mkemblem.c` | host tool: writes Emblem icons (`make tools`) |
| `tools/make_examples.py` | the package's example icons (and a render sheet of them) |
| `tools/make_lha.sh` | puts the release together: `dist/Emblem.lha` + `dist/Emblem.readme` (`OUT=` and `RELEASES=/nonexistent` for test builds) |
| `tools/iconset_build.py` | the glass icon set: mapping check, export, its own archive `dist/GlassIcons.lha` (package/iconset/README.md) |
| `tools/os4/mkicon.c` | guest helper that saves the package's native icons (package/icons/README.md) |
| `tools/render_sheet.py` | render sheets of composed icons (`step3`, `step4` or a JSON case list) |
| `tests/host/` | host tests: format codec, PNG decoder (PngSuite vs pypng), tool types, engine |
| `tests/host/render.c` | host renderer (`build/host/render`): the module's composition on the host |
| `tests/os4/run_os4.py` | guest test runner (MCPd, target os4-amigaone), steps 1-6 |
| `tests/os4/run_iconset.py` | guest test of the icon set's installer: install, update, Restore, install again, Remove |
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
tools/make_lha.sh               # dist/Emblem.lha (needs make os4 tools; checks the History entries)
tests/os4/run_os4.py --step=6   # the package: install, update, examples, remove (alone; resets the guest)
tools/make_art.py art --preview docs/step6_art.png   # redraw the art (then rebuild the package)
```

## Use (guest)

Install the package (Install script), or by hand:

```
Copy emblem.iconmodule LIBS:IconModules/     ; then reboot: icon.library opens modules at startup
EmblemIcon SYS:Devs                          ; show format and tool types
EmblemIcon SYS:Devs TO=EMBLEM                ; convert to the Emblem format
EmblemIcon SYS:Devs TO=AMIGA                 ; back to a native icon
EmblemIcon Work: ALL                         ; list the Emblem icons in Work: and below
EmblemIcon Work: ALL TYPE=DRAWER TO=EMBLEM SET="IMAGE=DrawerNS|EMBLEM=INTERNAL,30,30,33,30"
                                             ; every drawer: Emblem, with these tool types
```

Then add tool types to the Emblem icon, e.g. `IMAGE=DrawerNS`, `IMAGESELECTED=DrawerS` and
`EMBLEM=EmblemMusic,28,28,34,32`, with the PNGs in `ENVARC:sys/emblem/`. Programs that need the
icon's own images pass `EMBLEMA_NoCompose, TRUE` (src/emblem.h) to GetIconTags().

Needs AmigaOS 4.1: icon.library with module support (V51.15+) and z.library 53+.
