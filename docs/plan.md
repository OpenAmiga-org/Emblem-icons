# Emblem icon plugin: feasibility and plan

Project: openamiga.org project 34 "Emblem icon plugin" (created 2008-10-09 by orgin).
Status of this document: evaluation + plan, 2026-11-15; all six steps done (results in sections 9-14).
The 2008 code in openamiga SVN `projects/34/codeexamples` (Wet overlay code) is **not used** (user's
decision: old and stale). Everything is new code.

## 1. What the spec asks for (short)

- Per icon, tool types choose a **default image** (`IMAGE=`, `IMAGESELECTED=`) instead of the icon's own
  image, and an **emblem** drawn on top (`EMBLEM=`, `EMBLEMSELECTED=`), with size, position and a
  rendering method: `SHADOW`, `GLOW`, `GRAY`, `DARK`, `BRIGHT`, `NONE`.
- `Name,Method` for images, `Name,Width,Height,X,Y,Method` for emblems; missing method = global preference;
  missing X/Y = 0,0; width/height 0 or missing = the emblem's own size.
- `EMBLEM=INTERNAL,...`: the icon's own images become the emblem (then IMAGE/IMAGESELECTED must be set).
- Unknown image name: ignore that tool type. Emblems are clipped to the image they are drawn on.
- Images (24-bit + alpha, e.g. PNG) live in `ENVARC:sys/emblem`.
- Not all methods are needed in the first version.

## 2. How OS4 could host such a "plugin"

icon.library (V51.15+) has an official, documented plugin API: **icon modules**.

- Files `LIBS:IconModules/<name>.iconmodule`, opened by icon.library at startup.
- Interface `main` (SDK 54.25: `workbench/iconmodule.h`, `interfaces/iconmodule.h`,
  `Documentation/AutoDocs/iconmodule.doc`; in the walkero docker under
  `/opt/ppc-amigaos/ppc-amigaos/SDK/`): `ModuleControlA`, `LoadIconA`, `SaveIconA`, `AllocIconDataA`,
  `FreeIconDataA`, `DupIconDataA`, `ScaleIconA` (+ varargs versions).
- A module fills the empty DiskObject icon.library hands it (tool types, type, drawer data, images via
  `IconControl()`, ARGB through `ICONCTRLA_SetImageDataFormat IDFMT_DIRECTMAPPED`), attaches private data
  with `ICONCTRLA_SetIconModuleData`, and can save icons in its own format (`ICONPUTA_FileFormat`).
- Known module: png.iconmodule 53.1 (Massimo Tantignone, 2008, OS4Depot `library/misc/png_im.lha`).

## 3. Spike result (2026-11-15, QEMU guest, icon.library 54.6 (27.12.2015))

A logging do-nothing module (`spike/emblemspy.c`, always answers "not my format") was installed in the
guest and the guest rebooted. Observed (DumpDebugBuffer):

| What | Result |
|---|---|
| Module loaded at boot | yes: opened by "Background CLI"; queried formats/load/save/scale/convert support, then got IconBase + IIcon |
| Workbench loading all its icons at boot | **no LoadIconA call at all** |
| `GetIconTags("SYS:Devs")`, `SYS:Prefs` (native, format "Amiga", ARGB) | **no LoadIconA call** |
| `RAM:junk2.info` (4 KB, not an icon) | LoadIconA called (`icon` non-NULL, task = caller) |
| `RAM:junk.info` (25 bytes) | not called: icon.library first reads a 58-byte header; shorter files fail before modules |

The disassembly agrees: icon.library reads 58 bytes, checks magic `0xE310` version 1, and only when that
fails walks the module list.

**Conclusion: icon modules never see native .info icons.** A module cannot "filter" existing icons
(it cannot add an emblem to the unchanged `Sys:Devs.info`). It can only produce emblem icons from .info
files stored in **a format the module owns**.

## 4. Verdict

**Possible**, cleanly, with the official API, under one condition: icons that use emblems/default
images are stored in the module's own file format ("Emblem" format). A small tool converts an icon to
that format and back (both through icon.library, so the module does the writing). Every program that
uses icon.library (Workbench, Filer, DOpus, 68k programs) then shows the composed icon. No patching.

The only way to keep the native .info files unchanged would be to patch icon.library
(`SetMethod()` on `GetIconTagList`, `PutIconTagList`, `DupDiskObjectA`, ...). That works too, but it is
fragile (every save path must hand back the original images), it is exactly what icon.library's docs
discourage, and it isn't a "plugin". **Recommendation: the icon module route.**

## 5. Design (recommended route)

### 5.1 Pieces

| Piece | What |
|---|---|
| `emblem.iconmodule` | LIBS:IconModules; format name "Emblem"; load + save + convert support, no scaling (icon.library scales) |
| `EmblemIcon` (CLI) | `EmblemIcon FILES/M TO=EMBLEM\|AMIGA`, plus `SET` / `SHOW` for the four tool types; converts via `PutIconTags(..., ICONPUTA_FileFormat, "Emblem")` and back with `~0` (native) |
| `ENVARC:sys/emblem/` | default images and emblems (PNG, 32-bit) |
| `ENVARC:sys/emblem.prefs` | global settings, text: `METHOD=SHADOW`, `SELECTEDMETHOD=...` (prefs editor later, optional) |

### 5.2 The Emblem file format (own, documented in docs/format.md)

- Magic + version first (never `0xE310`, never a PNG signature), always at least 58 bytes.
- Holds everything a DiskObject carries: type, default tool, tool types, position, stack size,
  tool window, drawer data (incl. flags/view modes), frameless flag, and the icon's **own** two images
  as ARGB (zlib-compressed), with width/height.
- So converting back to "Amiga" loses nothing, and `INTERNAL` / "no IMAGE given" have the icon's own
  images to work with.
- Unknown chunks are kept on save (IMA_SetMaxUnknownDataSize rule).

### 5.3 LoadIconA

1. Read the header; not our magic → `ERROR_OBJECT_WRONG_TYPE` at once (cheap: modules are only asked
   about non-native files anyway).
2. Fill the DiskObject fields (all allocations with `FreeAlloc()` on the IMA_FreeList).
3. Parse IMAGE / IMAGESELECTED / EMBLEM / EMBLEMSELECTED (spec syntax), get images from the cache,
   compose normal + selected ARGB, set them with `IconControl()`.
4. Attach module data: own library base (first longword, as the autodoc advises), the original images,
   the composed buffers (to recognise them on save), unknown chunks.

### 5.4 SaveIconA / Dup / Free

- Save writes the attributes from the DiskObject and the **original** images from the module data, never
  the composed ones. If a client changed the images (icon editor), the new images become the icon's own
  images, unless they are byte-identical to the composed result (then the originals are kept: no
  emblem-on-emblem).
- `ICONPUTA_OnlyUpdatePosition` (snapshot): patch only the position in the file.
- DupIconDataA copies the module data; FreeIconDataA frees non-FreeList memory.

### 5.5 Image cache and loading

- Own PNG reader (8-bit gray/palette/RGB/RGBA, tRNS; interlace optional) with zlib linked in, or a
  public-domain decoder (stb_image, PNG only) with AllocVec allocators. **No datatypes**: they may call
  icon.library, and the autodoc warns against recursion.
- Decoded images cached by name, shared, under a SignalSemaphore; each use checks the file's date stamp
  so changed artwork shows after the next icon load. Size limit + LRU.

### 5.6 Composition (pure ARGB C code, built and tested on the host first)

- Scale emblem to W x H (box filter down, bilinear up), place at X/Y, clip to the base image.
- Methods: NONE, DARK (-25 %), BRIGHT (+25 %), GRAY (luma) first; SHADOW (+5,+5 soft alpha shadow:
  blur of the alpha, about 40 % black) and GLOW (outer glow: dilated, blurred alpha in a light colour) next.
- Method applies to the layer it names (image or emblem), as in the spec; default from emblem.prefs.

## 6. Steps

| Step | Content | Done when |
|---|---|---|
| 0 | Spike (done) | Facts in section 3 |
| 1 | Module skeleton + Emblem format, **no composition**; `EmblemIcon TO=EMBLEM/AMIGA` | **DONE 2026-11-15**, see section 9 |
| 2 | PNG reader + image cache, IMAGE= / IMAGESELECTED= | **DONE 2026-11-15**, see section 10 |
| 3 | Composition engine, methods NONE/DARK/BRIGHT/GRAY, positions, scaling, clipping, INTERNAL | **DONE 2026-11-15**, renders approved by the user, see section 11 |
| 4 | SHADOW, GLOW, emblem.prefs global method | **DONE 2026-11-15**, renders approved by the user, see section 12 |
| 5 | Robustness: missing files, bad tool types, huge images, 8-bit screens, low memory, many icons | **DONE 2026-11-15**, see section 13 |
| 6 | Sample artwork set (placeholder art from a script unless you have real art) + docs + LHA with Installer | **DONE 2026-11-15**, art and examples approved by the user, see section 14 |

Testing tools from the spike: `spike/iconload.c` (GetIconTags + format + tool types), DumpDebugBuffer
logging, guest reboot to reload modules (icon.library opens modules only at startup).

## 7. Risks and unknowns

- **Save routing** (step 1): if icon.library saved module-loaded icons as native "Amiga" by default, the
  composed image would be written into the file. The autodoc says saves go to the loading module unless
  another format is asked for; step 1 tests this before anything else.
- Programs that read .info files without icon.library would not understand Emblem files (rare on OS4).
- Icon editors that load, edit and save get the composed image; handled by the rule in 5.4, but the edit
  then happens on the composed picture.
- Only icon.library 54.6 tested; module support exists since 51.15. A newer icon.library on real
  hardware should be checked.
- Images in ENVARC: (disk) per spec; ENV: (RAM copy) would be faster but costs RAM. Kept as spec says
  unless you decide otherwise.

## 8. Decisions

1. Route: **icon module with own file format** (user, 2026-11-15).
2. Code: **GitHub repo orgin/emblemicon** (user, 2026-11-15), made **public** with release v1.0 (the
   package Emblem.lha) on the user's request the same day; nothing in openamiga SVN.
3. Names: **emblem.iconmodule, format "Emblem", EmblemIcon** kept (user, 2026-11-15); the package is
   called Emblem.
4. Artwork: **placeholders drawn by a script** (user, 2026-11-15): tools/make_art.py, public domain.
5. Image folder: **`ENVARC:sys/emblem`** as in the spec (user, 2026-11-15). Note: on this OS 4.1 ENV:
   is not copied at boot; it copies a file from ENVARC: the first time it is read and keeps that copy
   (seen in the guest), so the settings file is written to both.

## 9. Step 1 result (2026-11-15)

Done: `src/emblemfile.[ch]` (format codec, portable), `src/module.c` (emblem.iconmodule 1.0),
`src/emblemicon.c` (EmblemIcon 1.0), `docs/format.md`. Build and tests: see README.md.

Tests:
- Host (`make test`): 400 random icons round trip with and without zlib, minimal icon, unknown chunks
  kept, truncation and bit-flip fuzzing under ASan/UBSan.
- Guest (`tests/os4/run_os4.py --deploy`): 140/140 checks on 6 made icons (ARGB with/without selected
  image, palette with/without, planar, drawer) and 6 system icons (SYS:Devs, Prefs, Disk, Clock,
  MultiView, Prefs/Workbench): native -> Emblem identical (everything icon.library returns, CRCs of all
  image data), tool type edit + save stays Emblem, snapshot rewrites only the 8 position bytes, save
  after a Workbench-screen layout keeps everything, DupDiskObject + save stays Emblem and identical,
  Emblem -> native identical to the original.
- By hand in the guest: Workbench shows Emblem icons exactly like the native ones
  (docs/step1_workbench.png: top row native, bottom row `_E` = Emblem); the Workbench Information
  window reads them, and its Save keeps the Emblem format and the original images.

Learned (all now handled):
- **icon.library routes saves of a module-loaded icon back to that module** (the main risk in 7).
- The "empty" DiskObject icon.library gives LoadIconA is not cleared: the module sets every field.
- Chunky icons need a planar fallback image (`GadgetRender`) or DupDiskObject and native saves fail
  with 212; NewDiskObject() icons made chunky have the same problem (GetDefDiskObject ones don't).
- After a Workbench layout, `GadgetRender` of a chunky icon is an 8-plane copy remapped to the screen;
  the module keeps the file's own fallback and gadget size for saving.
- The module uses z.library 53 (present in the guest, 53.11) for image compression; without it, icons
  are saved uncompressed and compressed ones can't be loaded.
- GCC 15 + SDK: `va_getlinearva()` must be replaced (see LINEARTAGS in module.c); the module links
  with `-nostdlib` and its own memcpy/memset.

Known limits, for later steps:
- EmblemIcon takes no wildcards yet.
- Converting a native chunky icon that some program has already laid out on a screen would store the
  remapped fallback (EmblemIcon itself loads without remapping, so it does not happen there).
- Leave Out and copying by Workbench were not tried separately (Leave Out is a snapshot-type save,
  copy is a plain file copy).

Guest state: emblem.iconmodule 1.0 stays installed in LIBS:IconModules of the QEMU guest (affects only
Emblem files).

## 10. Step 2 result (2026-11-15)

Done: `src/png.[ch]` (PNG decoder: all colour types and depths, tRNS, Adam7; inflate through
z.library), `src/imagecache.[ch]` (decoded images by name), `src/emblemspec.[ch]` (the four tool
types, spec syntax), `src/compose.[ch]` (ARGB helpers), `src/emblem.h` (public: format name, image
folder, `EMBLEMA_NoCompose`). emblem.iconmodule shows IMAGE= / IMAGESELECTED= default images.

How it behaves (decisions taken where the spec leaves room; easy to change):
- `IMAGE=Name` loads `ENVARC:sys/emblem/Name.png`; a name with a dot is used as it is; sub-drawers
  are allowed, `:` and a leading `/` are not. Keys are case-insensitive and must be written exactly
  (`IMAGE=`, no space before `=`), the first occurrence counts: the same rules as FindToolType().
- Without IMAGESELECTED the selected image is the icon's own selected image if it has one, else
  none (icon.library's select effect on the default image). Without IMAGE the normal image is the
  icon's own.
- An icon's two images share one size: the selected image is centred on the normal image's size and
  clipped.
- Missing, broken or larger than 256 pixels images are ignored (the icon shows its own image).
- Image files are checked for changes at most every 2 seconds; then the next icon load shows the new
  artwork. Up to 64 images / 8 MB of pixels stay in memory.
- The Method field (`IMAGE=DrawerNS,NONE`) is read but not used yet (steps 3-4).
- Saving always writes the icon's own images: the module keeps the file's image chunks with the icon
  and a CRC of the composed images; if a program gave the icon new images (CRC differs), those become
  the icon's own. `EmblemIcon` loads with `EMBLEMA_NoCompose`, so converting back to a native icon
  never bakes a default image in.

Tests:
- Host (`make test`): PNG decoder against pypng on all 162 PngSuite images (identical pixels), the 14
  corrupt ones rejected, 6480 fuzzed decodes and truncations under ASan/UBSan; tool type parser and
  ARGB helpers.
- Guest (`tests/os4/run_os4.py --deploy`): 194/194 (step 1's 140 plus 54): default images shown with
  the right pixels on ARGB, palette, planar, drawer and system icons; the icon's own images survive a
  save of a composed icon, a save after a Workbench layout, DupDiskObject and the conversion back to
  native; missing / too large / malformed / disabled `(IMAGE=...)` tool types ignored; five PngSuite
  images decode on the big-endian guest exactly as on the host; a changed PNG shows after the 2 s
  re-check; new images set by a program become the icon's own.
- Workbench: docs/step2_workbench.png (B01: bottom row Emblem drawers with IMAGE=, B02: one selected,
  showing IMAGESELECTED).

Load time per icon in the QEMU guest (200 loads, varies between runs): native 3.3 ms, Emblem 3.4 ms,
Emblem with a default image 4.3-6.4 ms.

Learned:
- icon.library zeroes the colour of fully transparent pixels when it saves a native ARGB icon.
- Native icons raise small stack sizes (4242 came back as 8000 after a native save).

Guest state: ENVARC:sys/emblem exists (empty); the test images are deleted after each run.

## 11. Step 3 result (2026-11-15)

Done: the composition engine in `src/compose.c` (`cp_compose`, `cp_scale`, `cp_over`, `cp_method`,
`cp_emblem_size`), used by the module and by the host renderer `build/host/render`
(tests/host/render.c). Integer arithmetic only, so the guest and the host produce the same pixels.
`tools/render_sheet.py` makes render sheets; demo art in docs/art (drawn for the tests, not final art).

Renders: **docs/step3_renders.png** (R01-R12: normal and selected image at 2x, with the tool
types), **approved by the user 2026-11-15**, including the behaviour choices below. On Workbench:
docs/step3_workbench.png (W01).

How it behaves (decisions where the spec leaves room; easy to change):
- Size: `0,0` = the emblem's own size; **only one of width/height 0 = keep the aspect ratio** (the spec
  could also be read as "that dimension's own size", which distorts).
- Scaling: area average when shrinking, bilinear when growing, in premultiplied alpha (no dark fringes).
- Position X,Y = the emblem's top left corner on the image; negative values and overhangs are clipped
  to the image.
- DARK = colours x 0.75; BRIGHT = 25 % of the way to white (x 1.25 would burn out light colours);
  GRAY = luminance (Rec. 601). The method of IMAGE= applies to the default image, the method of
  EMBLEM= to the emblem.
- EMBLEM goes on the normal image, EMBLEMSELECTED on the selected one. **Without EMBLEMSELECTED the
  selected image has no emblem** (as the spec says; visible in R05-R08, R11, R12). If there is no
  selected image at all (no IMAGESELECTED, no own selected image), none is made and EMBLEMSELECTED is
  ignored: icon.library's select effect then works on the normal image with its emblem.
- INTERNAL only works together with a found IMAGE (EMBLEM) / IMAGESELECTED (EMBLEMSELECTED), as the
  spec asks; EMBLEMSELECTED=INTERNAL uses the icon's own selected image, else its normal one (R10).
- Emblem sources up to 1024 pixels, scaled emblems up to 512; larger ones are ignored.
- No method given: NONE until the global preference of step 4. SHADOW and GLOW are read but drawn
  like NONE until step 4.

Tests:
- Host (`make test`): engine unit tests (scaling, compositing, methods, size rule, every decision of
  cp_compose, out of memory at each allocation, 2000 random tool type sets under ASan/UBSan).
- Guest: 278/278 (`run_os4.py --deploy`): step 3 adds 42 cases (ARGB with/without selected image,
  palette, planar, SYS:Devs, SYS:Disk x 7 tool type sets): the module's pixels are exactly the host
  renderer's, and the icon's own images stay in the file.

Learned: the test icons from `icontest make` carried an active `EMBLEM=` tool type; the first key
counts, so it now is `(EMBLEM=...)`.

## 12. Step 4 result (2026-11-15)

Done: SHADOW and GLOW in the engine (`cp_effect` in src/compose.c, integer only like the rest), the
settings file parser `src/emblemprefs.[ch]`, and the module reading it (`ic_prefs` in
src/imagecache.c). The host renderer takes the same file with `--prefs`.

Renders: **docs/step4_renders.png** (S01-S12, normal and selected at 2x, tool types in blue, prefs
file text in red), **approved by the user 2026-11-15**, including the choices below. On Workbench:
docs/step4_workbench.png (W02).

The settings file `ENV:sys/emblem.prefs` (else `ENVARC:sys/emblem.prefs`), KEY=VALUE lines, `#` or `;`
comments, re-read within 2 seconds of a change:

| Key | Default | Meaning |
|---|---|---|
| `METHOD` | NONE | method for tool types without one (images and emblems) |
| `IMAGEMETHOD` | NONE | only for IMAGE=/IMAGESELECTED= (wins over METHOD) |
| `EMBLEMMETHOD` | NONE | only for EMBLEM=/EMBLEMSELECTED= (wins over METHOD) |
| `SHADOWOFFSET` | 5,5 | -16..16 (spec: +5,+5) |
| `SHADOWBLUR` | 2 | 0..8 (0 = hard) |
| `SHADOWOPACITY` | 50 | percent, black |
| `GLOWSIZE` | 2 | 1..8 |
| `GLOWOPACITY` | 80 | percent |
| `GLOWCOLOR` | FFFFFF | RGB hex |

How it behaves (decisions; easy to change):
- SHADOW: the layer's alpha, moved by the offset, blurred (box blur of the radius, twice), black at
  the opacity, drawn under the layer. GLOW: the alpha grown by GLOWSIZE, then blurred the same way,
  in the glow colour, under the layer.
- On an emblem the effect goes under the emblem; on a default image (IMAGE=Name,SHADOW) under the
  image. Everything stays inside the image's rectangle (spec), so an emblem outside the image can
  still cast its shadow in (S05 shows a shadow cut at the edge).
- Without a settings file nothing changes for existing icons (NONE). The plan's installer (step 6)
  could ship one with `EMBLEMMETHOD=SHADOW`, the spec's example.
- The extra keys (offsets, blur, opacity, glow colour/size) are not in the spec; they cost little and
  make the effects fit other Workbench backgrounds (a white glow hardly shows on a light window, W02).

Tests:
- Host: prefs parser (defaults, keys, priority of the specific keys, comments, CRLF, bad values),
  effects (shadow position/softness/opacity, glow colour and reach, clipping, shadow of an emblem
  outside the image, SHADOW on a default image, prefs methods), random tool types with effects under
  ASan/UBSan. The approved step 3 sheet renders byte for byte the same.
- Guest: 195/195 for steps 3+4 (`run_os4.py --deploy --step=3 --step=4`): step 4 adds 55 cases
  (built-in settings, a SHADOW prefs file, a GLOW/GRAY prefs file with CRLF and a comment, and one in
  ENVARC: only) x ARGB, palette and SYS:Devs icons: module pixels = host renderer pixels, own images
  kept. Full run of steps 1-4: 388/388.

## 13. Step 5 result (2026-11-15)

Guest scenario tests (`tests/os4/run_os4.py --step=5`, sections with `--only=bad,png,tt,huge,screens,wb,par,mem,speed`);
the whole suite (steps 1-5) passes: **497/497**, no crash report in the kernel debug buffer.

| Scenario | Result |
|---|---|
| 1159 broken Emblem files (every truncation, chunk lengths 0/-1/+1000/huge, impossible sizes, kinds, compression, palette, depth, newer version, unterminated tool types, 600 random byte changes; tests/os4/make_bad_files.py) | 121 load, 1038 fail cleanly; Workbench opens the drawer of all of them |
| 17 odd but valid files (no drawer data, no images, 200 KB of tool types, unknown chunks) | all load; Workbench opens the drawers |
| 52 broken PNGs as IMAGE= and EMBLEM= (PngSuite x*.png, truncations, bit flips with and without fixed CRCs, empty file) | all icons load and show their own image; pixels = host renderer |
| odd tool types (5000-character values, 20 KB line, 50-digit numbers, far positions, 500 lines of binary junk, 300 EMBLEM= keys, empty fields) | pixels = host renderer |
| large images: 1024x1024 emblem scaled to 512 and 48, 1025 wide, a 2.1 MB PNG, 256 and 257 default images | the ones over the limits are ignored; the rest = host renderer |
| 8-bit and 4-bit screens: lay out, draw, save (docs/step5_screen8.png, W04) | drawn; saving keeps the icon's own images |
| Workbench menus via ARexx: Snapshot, Copy, Leave Out, Put Away | still Emblem, own images kept, the copy is identical |
| 3 programs loading composed icons at once (300 loads each) | right pixels, no crash |
| memory: 400 composed and 400 raw loads | 0 bytes lost |
| low memory (memeater leaves ~2 MB of private memory) | the emblem can't be decoded, the icon shows its own image; afterwards it is decoded and shown again |
| 200 icons in a drawer (docs/step5_200icons.png, W03) | see below |

Bugs found and fixed:
- **An icon without any image crashed icon.library** (DSI in GetIconTagList) - possible with a damaged
  file. The module now gives such an icon a 16x16 frame image.
- **Workbench refused to open a drawer whose icon has no drawer data.** Disk, drawer and trashcan
  icons without a DRAW chunk now get default drawer data (box of def_disk).
- A default image or emblem that could not be decoded **for lack of memory** was remembered as
  broken until its file changed; the settings file likewise. Both are now read again at the next
  check (2 s).
- The image cache could in theory evict an image while a composition still used it (several huge
  images over the 8 MB limit); eviction now waits until the composition is done.

Speed (QEMU guest, load + layout on the Workbench screen, per icon, 3 x 200 icons; QEMU timings vary
by about +-0.5 ms between runs):

| | native | Emblem | Emblem composed (test art) |
|---|---|---|---|
| before the work of this step | 6.2 ms | 6.0 ms | 9.7 ms |
| after | 6.0 ms | 5.1 ms | 8.0 ms |

- Measured with a profiling build of the module (`make os4-profile`, prints phase times to the debug
  buffer; never shipped). Changes: the icon's own images are unpacked only when they are shown or
  used (saves ~0.8 ms per icon with IMAGE+IMAGESELECTED); scaled emblems are cached per name and size
  (a 1024 -> 512 emblem: 164 ms -> 12 ms per icon); a cheap fingerprint replaces the CRC that tells a
  save whether a program changed the composed images.
- The module's own share of loading a composed icon (IMAGE+IMAGESELECTED+EMBLEM) is now about
  1.2-1.3 ms, less than a plain Emblem icon (1.6 ms). **The remaining difference is in icon.library's
  layout of the composed pictures**, which depends on their content: composing with the Devs picture
  itself as IMAGE= is 6.4-7.1 ms, while the test art (large semi-transparent areas, shadows) is ~8 ms.
- Not done: caching whole composed images (would help drawers full of identical icons only).

## 14. Step 6 result (2026-11-15)

Done: the release package **dist/Emblem.lha** (`tools/make_lha.sh`, also copied to the shared folder's
releases/) with the readme `dist/Emblem.readme` (OS4Depot format, not submitted).

| Piece | What |
|---|---|
| `art/` | sample art, drawn by `tools/make_art.py` (public domain, placeholder): DrawerNS/DrawerS, DocumentNS/DocumentS (64x64), 17 emblems (32x32). Sheet: docs/step6_art.png (A01-A21, package icons P01-P13). The package ships only the 11 the examples use (`tools/make_examples.py --images`; DrawerNS/S + 9 emblems) |
| `package/Emblem/RemoveSamples` | AmigaDOS script (IconX icon P13): deletes the sample images of this and every earlier version from ENVARC:/ENV:sys/emblem, nothing else; asks first, QUIET for Install's Remove. Installed with the documentation; `tools/make_lha.sh` checks it names every shipped sample |
| Examples | ten Emblem icons written on the host (`tools/mkemblem.c`, `tools/make_examples.py`), one feature each; renders docs/step6_examples.png (X01-X10, with the installer's default EMBLEMMETHOD=SHADOW) |
| `package/Emblem/Install` | Installation Utility script: install, update (asks before replacing sample images, keeps the settings and the user's images) and remove |
| `package/Emblem/Emblem.guide` | AmigaGuide manual: install, quick start, tool types, methods, settings, images, EmblemIcon, examples, removing, programmers |
| `package/icons/` | the package's native icons, saved by the guest's icon.library (`tools/os4/mkicon.c`) |
| EmblemIcon | new: patterns and `ALL` (drawer trees, links not followed); in such runs only Emblem icons are shown or converted back, with a count at the end |

Install puts emblem.iconmodule in LIBS:IconModules, EmblemIcon in C:, the art in ENVARC:sys/emblem, the
settings in ENVARC:sys/emblem.prefs and ENV:sys (asks: SHADOW, GLOW or NONE for emblems without a
method; SHADOW by default), the guide, LICENSE.txt, Emblem-format.txt and the examples in
SYS:Documentation/Emblem (asks where). Remove first converts the Emblem icons in the drawers or
volumes the user picks back to native icons (`EmblemIcon <dir> ALL TO=AMIGA`), then deletes the
documentation, the sample images (choice: also the user's own, or none), the settings, EmblemIcon and
the module. A restart loads or unloads the module.

Tests: `tests/os4/run_os4.py --step=6` (alone: it resets the guest three times), **115/115**: a guest
without Emblem (module not in memory) → the package unpacked with the guest's LhA → Install run by the
Installation Utility in Novice mode (`ENV:EmblemInstallTest`, welcome window clicked) → every file in
place, the installed binaries are the built ones, settings in ENVARC: and ENV: → update run: no
settings question, settings and a user's own image kept → restart: module in memory, all ten examples
composed exactly like the host renders (art/ + the installed settings), `EmblemIcon ... ALL` finds 10 →
Workbench (docs/step6_workbench.png, W05) → a user's Emblem icon in SYS:, then Remove (22 s, scanning
all of SYS:) → that icon is native again with its own picture and tool types, everything removed but
the user's own image → restart: no module; the file lists of LIBS:IconModules, C:, ENVARC:sys, ENV:sys
and SYS:Documentation are the same as before the install.

Learned:
- ENV: on this OS 4.1 copies a file from ENVARC: the first time it is read and then keeps its copy, so
  settings are written to both, and the guide says to copy a changed file to ENV:sys.
- The Installation Utility writes its log only when it ends; in test mode the script ends without its
  last window.
- AmigaDOS `;` starts a comment: several commands in one exec_cmd need new lines.

The art (A01-A21, P01-P12) and the examples (X01-X10) were **approved by the user 2026-11-15**.

Not done: the art is placeholder art; the readme is not submitted to OS4Depot (only on the user's go).


## 15. The settings in the icon file (1.1, 2026-11-16)

Found in the live test of the glass icon set: some Prefs editors (WBPattern and others) refused to start
once their icons were Emblem icons; after Restore they worked again. Cause: they read all of their icon's
tool types as `ReadArgs()` arguments, so `IMAGE=`, `EMBLEM=` ... are unknown arguments. Of SYS:Prefs, 18
failed (ASL, Compatibility, Console, DOS, GUI, Palette, Pointer, PopupMenu, Printer, PrinterPS,
ScreenMode, Screens, Serial, Sound, Time, Timezone, WBPattern, Workbench). Bracketed tool types would be
skipped by them, but the user chose to move the data into the icon file, with an editor (EmblemIcon now,
a GUI later); existing Emblem icons are not converted (nothing public used the tool types yet).

- **Format:** new chunk `ESET` (docs/format.md): the settings as packed NUL-terminated `KEY=value`
  strings, like TTYP. Module 1.0 keeps it as an unknown chunk.
- **Module 1.1:** composes from ESET only (an `IMAGE=` tool type does nothing now); keeps the settings
  with the icon (EmblemData), so every save (Information window, snapshot, layout, DupDiskObject) keeps
  them. `EMBLEMA_GetSettings` (GetIconTags, STRPTR **: NULL-terminated array on the icon's FreeList) and
  `EMBLEMA_SetSettings` (PutIconTags, STRPTR *: replaces them in the file) in src/emblem.h.
- **EmblemIcon 1.2:** SET/UNSET with the four keys change the settings, other keys the tool types; a
  setting implies TO=EMBLEM (TO=AMIGA with one is an error: native icons can't keep them); the listing
  shows "Tool types:" and "Settings:" apart; every saved setting is checked after loading the icon again.
- **mkemblem** `ES=` (TT= refuses the four keys), the examples and the icon set (Scripts/Convert with
  EmblemIcon SET) write settings; the set's Install needs module 1.1 and EmblemIcon 1.2.
- **Tests:** host format test (ESET round trip, unterminated, twice); guest: `icontest tt` routes the four
  keys to the settings (`ttonly` keeps them as tool types), dumps show `es=` lines, the host render takes
  the settings.

Results (QEMU guest, 2026-11-16): host tests OK; `run_os4.py` steps 1-5 all pass (1+3+5: 364/364 after
the test fixes below, 2 and 4 passed in the first run), step 6 with the test build
(`--plugin=build/test/Emblem.lha`) 101/101 (one expectation fixed first: after Remove the user's icon is
native, so its settings are gone); `run_iconset.py` 64/64 (the settings of SYS:Prefs/Printer are in the
file, none in its tool types; 7 icons composed exactly like the host); new **`run_prefs.py`**: with the set
installed, **all 33 Prefs editors the set changes start from Workbench** with their own window (WBPattern:
"WBPattern preferences" 546x434 instead of the requester), 37/37.

Learned: the test icons of step 1 already carry NEWTT=1 when the SET test starts (use other keys); an
installed package leaves ENV:sys/emblem.prefs with EMBLEMMETHOD=SHADOW, which the expected pixels of steps
2, 3 and 5 don't assume, so run_os4.py deletes it first; a Prefs editor that runs already opens no second
window.

## 16. Workbench's Information window and Emblem icons (2026-11-17)

The user asked to test that the Information window (RAWBInfo; its menu can replace the icon's image)
and Emblem icons don't break each other. Tried by hand on Emblem icons (a tool, a project, a drawer),
then automated: **`tests/os4/run_wbinfo.py` 21/21**. The settings were kept in every case but one
(Load default icon replaces the whole icon with the normal default icon, as the window warns).

Found and fixed in the module:
- **Delete alternate image** and **Paste** (which replaces only the normal image) baked the composed
  picture into the icon's own image: when a program changes one of the two composed images, the
  other one is now the file's own again (`keep_own()`; `ef_parse_imag()` reads one IMAG chunk).
- **Drop planar data** did nothing: the module now honours `ICONPUTA_DropPlanarIconImage` (no planar
  fallback in the file; made again at load).
- **Default + Restore** left the aspect byte 0x40 (4:0, no ratio): an aspect with a 0 half is now
  saved as unknown.

Works as it is: save without a change (nothing written), tool types and stack, Frameless, Default (the
own image becomes the default tool's, the settings stay, so the composed picture is the same), Load (a
PNG), a drawer's Show/View, type change, Save as default "tool" (def_tool becomes the Emblem icon).
Note for the guide: after Default/Paste/Load the window shows the new own picture, but the saved icon
still shows the composed one (IMAGE= covers it).

**EmblemInfo** (docs/embleminfo.md, src/embleminfo.c): the user chose a separate editor for the new
icon type instead of a copy of the Information window. First version 1.0 runs in the guest
(docs/embleminfo_v1.png): preview by the module, image/emblem names with file requesters (relative to
ENVARC:sys/emblem, files elsewhere copied there on request), the icon's own picture as the emblem,
size, position, effects, "same emblem when selected", Normal/Emblem format (asked before settings are
dropped). Checked by hand: edit + Save writes only the settings; normal → Emblem → normal gives back
the original icon exactly.
