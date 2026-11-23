# Glass icon set: inventory and grouping proposal

For Emblem 1.1 (user's decision 2026-11-15). Style: the approved glass preview
(docs/iconsets/glass/glass_preview.png): glenz glass, glowing light-blue hairline edges, objects facing
down right, floor reflection; emblems as glass tiles in deep red, green, blue and violet (R3, G3, B3, V3).
Made group by group; each group is decided together before it is drawn.

## What a stock OS 4.1 FE Update 3 Workbench has (QEMU guest, 2026-11-15)

- `ENVARC:Sys`: 167 entries: about 95 default icons (`def_*`) for files, disks and devices, 45 mouse
  pointers (`def_*pointer`), 3 frames, 3 overlays, `disk_system`, `disk_work`.
- `SYS:`: 12 top-level drawers, 35 Prefs editors, 25 Utilities, 15 System programs, 6 Storage
  drawers, Internet and Emulation drawers, documentation.

## Tested: default icons can be Emblem icons

`ENV:Sys/def_ascii.info`, turned into an Emblem icon with `IMAGE=GlassFile` and
`EMBLEM=GlassStar,0,0,36,35`, was used by Workbench for a text file without an icon, composed by the
module (glass file image with the star emblem). So one "file" base plus a type emblem covers every
file type through the def_ icons, with no change to Workbench or DefIcons.

## Three kinds of icon

| Kind | What | Example |
|---|---|---|
| **A. generic** | one shared base image + an emblem that says what it is | every drawer = glass drawer + emblem; every picture file = glass file + picture emblem |
| **B. unique** | an image of its own + a common emblem for its family | each Prefs editor its own glass object + the prefs emblem |
| **C. left alone** | not icons, or better kept as they are | mouse pointers, frames, overlays |

## General rule (user, 2026-11-15)

Files and drawers that have no .info file in a normal OS 4.1 install (C, L, S, Libs, Classes, Locale,
SObjs, Fonts, Kickstart, the Storage subdrawers AudioModes, Internet, Languages, Locale, most files; the full list is in docs/iconset_inventory.md) keep having none: they inherit the
default icon for their type. For them the work is the def_ icon in the new style (for drawers just
`def_drawer`). Hardly anyone shows files without icons on Workbench, and file managers usually show
no icons anyway.

## Drawers are drawers (user, 2026-11-16)

Every icon that belongs to a drawer is the glass drawer + an emblem, never an object of its own, so
no drawer is drawn as a program by mistake (Presets in Prefs was, and was corrected). The kind of
every icon comes from the guest, not from memory: `docs/iconset_inventory.md` (made by
`tools/iconset_inventory.py` from a `List ... LFORMAT "%P%N|%L"` of the guest), and before each batch
`tools/iconset_inventory.py build/work/inventory.txt check NAME...` must report no drawer.

Drawers with icons of their own below the top level (found 2026-11-16; ALL APPROVED 2026-11-16, sheets
docs/iconsets/glass/sub_*.png, program emblems progemblems.png):

| Where | Drawers with an icon |
|---|---|
| SYS:Prefs | Presets (decided: EmPresets, blue) |
| SYS:Utilities | AmiGS, AmiPDF, Blankers, Commodities, Dockies, Ghostscript, SGrab (APPROVED, sub_utilities.png) |
| SYS:System | AmiUpdate, Python (APPROVED, sub_system.png) |
| SYS:Internet | Action logs, Connection logs, Connections, Reports, Templates (APPROVED, sub_internet.png) |
| SYS:Emulation | AmigaDisks, AmigaROMs (APPROVED, sub_emulation.png) |
| SYS:MUI | Demos, Docs, Icons, Images, Libs, Patterns, Presets, Rexx (APPROVED, sub_mui.png) |
| SYS:Storage | Datatypes, DOSDrivers, KeyMaps, Monitors, NetInterfaces, Printers (APPROVED, sub_storagedevs.png) |
| SYS:Devs | DataTypes, DOSDrivers, KeyMaps, Monitors, NetInterfaces, Printers (APPROVED, sub_storagedevs.png) |
| SYS:Documentation | AmiSSL (APPROVED, sub_documentation.png; SFTPHandler is ours, not stock) |

(Correction: the Storage and Devs subdrawers DO have icons in a stock install; they are drawers.)

**Decided with the user 2026-11-16:** each sub-drawer emblem takes its PARENT drawer's emblem colour
(Devs violet, Storage green, MUI and Internet blue, Emulation green, Utilities violet, System red,
Documentation violet); the symbol says what the drawer holds, so Storage and Devs share symbols and
differ by colour (stored / active). Program drawers (AmiGS, AmiPDF, Ghostscript, SGrab, AmiUpdate,
Python): our own glass emblems designed after how their icons look today (looked at on the guest).
Reviewed per parent drawer, a sheet each, symbols drafted first. The user (2026-11-16): for a program drawer, look INSIDE it at the main program's own icon first
(larger, and without the stock blue drawer). References kept in docs/iconsets/glass/reference/:
os41_program_icons.png (AmiGS: page + PS + magnifier; AmiPDF: page + PDF swoosh + magnifier;
Ghostscript: no program icon, its drawer shows a printer; SGrab: a camera; AmiUpdate: a gear with a red
button; Python: a Boing ball with a ring), os41_utilities.png, os41_system.png and
os41_category_drawers.png (the stock drawer symbols of Internet, MUI, Storage, Devs, Emulation).

## Proposed groups, in the order to make them

### 1. Drawers (A)

One base: the glass drawer (closed; selected = open). An emblem per role:

| Drawer | Emblem |
|---|---|
| Prefs | prefs (gear) |
| Utilities | tools (wrench) |
| System | system (chip) |
| Storage | storage (stacked plates) |
| WBStartup | startup (power) |
| Devs, Storage/DOSDrivers, Monitors, Printers, KeyMaps, NetInterfaces, Datatypes | devices (plug) / per drawer? |
| Fonts, Locale, Libs, Classes, C, L, S, SObjs, Kickstart | system or code emblems? |
| Internet | internet (globe) |
| Emulation | games? / Amiga (boing ball?) |
| Documentation | text/book |
| MUI | ? |
| any other drawer (def_drawer) | none |

**APPROVED by the user 2026-11-16** (docs/iconsets/glass/drawers.png: DR01 def_drawer, DR02-DR11 SYS: drawers, normal + selected).

**Decided (user, 2026-11-15):**
- The SYS: drawers that have icons each get their own emblem (table above).
- Drawers without icons (C, L, S, Libs, ...): no icons; `def_drawer` becomes the glass drawer.
- Program drawers (e.g. Work:IBrowse): `EMBLEM=INTERNAL`: the glass drawer with the drawer's own
  picture as the emblem, converted with `EmblemIcon ... TYPE=DRAWER TO=EMBLEM SET=...` (EmblemIcon 1.1).
- Emblem placement: **lower right** (`EMBLEM=Name,0,0,36,35`), chosen from docs/iconsets/glass/drawers.png
  (user, 2026-11-16).
- Emblems: see-through coloured glass, not painted: less opaque, with Tron-style glowing edges
  (user, 2026-11-16).
- **No emblem may contain the old generic drawer** (user, 2026-11-16). Many program drawers'
  pictures are the stock drawer, some with a logo painted on (Work:Games/Settlers2), so INTERNAL on
  them is wrong. A program drawer gets the glass drawer and, as its emblem, only a real logo or the
  program's own picture (e.g. the tool icon inside the drawer) when there is a usable one; otherwise
  no emblem. How to supply those emblems is still open (a logo image per program, or a tool that
  takes the picture of the program's icon).

### 2. Disks and devices (A, a base per physical kind)

| Base | def_ icons |
|---|---|
| hard disk (the glass drive) | def_disk, disk_system (+ system emblem), disk_work (+ work/home emblem), def_hdf |
| floppy | def_DF0-3, def_FD0-1, def_PC0, def_crossdos |
| optical disc | def_CD0-6, def_cd, def_dvd, def_cdda |
| RAM | def_ram, def_RAD |
| removable (stick/cartridge) | def_zipdisk, def_jazdisk, def_modisk, def_pccard (USB too) |
| network | network volumes (handlers like SFTP:, Nextcloud). (def_ftp and def_http are NOT here: on the guest they are project icons opened by MultiView, i.e. files; they are in group 3, the page + globe, FT03) |
| bad disk | def_baddisk (+ warning emblem) |
| trashcan | def_trashcan, SYS:Trashcan: empty / full (selected) |

**Decided (user, 2026-11-16):** all these kinds (hard disk = the glass drive; floppy, optical disc, RAM
module, removable = USB stick, network node, bad disk = drive + warning emblem, trashcan empty/full);
disk_system and disk_work = the same glass drive with an emblem (system / home); a device's selected
image = the same object lit from inside (brighter edges and inner light).

**APPROVED by the user 2026-11-16** (docs/iconsets/glass/devices.png, devices_flip.gif, disc_final.png):
DV01-DV10. The disc: clear, low refraction (IOR 1.12, so it does not look like a horn), turned 8 degrees
right and leaning back 25 degrees, no metallic data layer. The floppy's selected image: the shutter slides
left by about a fifth of its width (like a real 3.5" floppy), its window then over the access hole;
approved 2026-11-16 (floppy_final.png, floppy_flip.gif).

### 3. Files by type (A, through the def_ icons) — APPROVED 2026-11-16

Sheet: docs/iconsets/glass/files.png, files_flip.gif (FT01-FT14, AR01-AR11).

**Decided with the user 2026-11-16:** every file type uses the approved G05 glass page (with its text
lines) plus a type emblem lower right; plain text and def_project have no emblem. Archives use the
glass crate (G08) plus a tile with the format letters. Selected image: something moves, only that part
(the page's folded corner lifts; the crate's lid lifts), same framing; no glow.

**Page selected state, APPROVED 2026-11-16** (the user's own design, PG6, docs/iconsets/glass/page_split.png,
page_split_flip.gif): the page splits in two. The back part (no fold) stays in place; the front part is a
single thin page (with the fold and the lines) turned 30 degrees towards the viewer on the left edge,
where the two stay joined. Rejected: the corner lifting (PG1-PG3), the page hovering (PG4), two equal
halves (PG5). Then (user): the normal image is the same two parts closed, the fold on the front page
only, the back part's full corner behind it (PG7, docs/iconsets/glass/page_split.png). APPROVED 2026-11-16.

**Crate selected state, APPROVED 2026-11-16:** lid opened 25 degrees on the back hinge (user's pick); the body
open at the top (no second lid under the lid), a third small crate stacked inside so the contents show
in the opening; the straps are bands on the outside, the one over the top only while closed (LD5,
docs/iconsets/glass/lid_variants.png).

| Emblem (colour) | def_ icons |
|---|---|
| none (plain page) | ascii, ftxt, rtf, tex, file, project |
| EmDocument, new (violet) | pdf, ps, eps |
| EmInternet, globe (blue) | html, http, ftp |
| EmDocs, book (violet) | guide, amigaguide |
| EmPicture (blue) | picture, ilbm, jpeg, gif, png, bmp, tiff, brush, animbrush |
| EmMusic (red) | sound, 8svx, aiff, aifc, wav, mp2, mp3, mpa, ahx, sfx, cdda |
| EmVideo, new (red) | video, anim, avi, mpeg, wmv, asf, cdxl |
| EmCode, new (green) | script, arexx, py, pyc, php, js, make, fd, install (Installer scripts) |
| EmFont, new (violet) | font, outlinefont |
| EmSystem, chip (red) | library, datatype, loadmodule, kickstart, bin, sys, system |
| EmDevs, plug (violet) | device, handler, filesystem, mount, monitor |
| EmMUI, window (blue) | mui |
| EmPrefs, gear (blue) | prefs |
| EmStorage, stack (green) | hdf, mdf (disk images) |

Archives (crate + letters, green): lha and lharc LHA, lzx LZX, zip and pkzip ZIP, gzip GZ, bz2 BZ2,
tar TAR, 7zip 7Z, arj ARJ, rar RAR, zoo ZOO; def_archive = the crate without a tile.

Tools without an icon of their own: def_tool = the glenz crystal (G10); selected (user 2026-11-16): the crystal
risen and lit from within, the beam to its pedestal longer and brighter (ICON tool_open; docs/iconsets/glass/crystal.png). APPROVED.

### 4. Programs (B: their own image + a family emblem)

| Family | Programs | Family emblem |
|---|---|---|
| Prefs editors (35) | AHI, AmigaInput, ASL, Compatibility, Console, DefIcons, DOS, Font, GUI, Input, Internet, Locale, Notifications, Palette, Picasso96Mode, Pointer, PopupMenu, Presets, Printer, PrinterGfx, PrinterPS, ScreenBlanker, ScreenMode, Screens, Serial, Sound, Time, Timezone, UBoot, Updates, URL, USB, WBPattern, WBStartup, Workbench | prefs |
| Utilities (20 programs) | Calculator, Clock, FileCompare, GraphicDump, IconEdit, InitPrinter, Installation Utility, KeyShow, LogViewer, MEmacs, MultiView, NotePad, PartitionWizard, PlayCD, PrefsObjectsEditor, PrintFiles, RawDisk, ShowConfig, UnArc, USBInspector (DRAWERS, not programs: AmiGS, AmiPDF, Blankers, Commodities, Dockies, Ghostscript, SGrab) | none (decided) |
| System (13 programs) | BIOSUpdater, Find, FixFonts, Format, FormatCDRW, GrimReaper, Help, Mounter, RexxMast, RinghioServer, Shell (icon only), TypeManager, Media Toolbox (DRAWERS: AmiUpdate, Python) | none (decided) |
| Internet | Edit Connection, New Connection, Open Connection (icons only; decided 2026-11-16: the DV08 network globe + a blue emblem: plug SdConnections / + EmConnNew / pencil EmConnEdit, selected lit from inside; docs/iconsets/glass/internet_icons.png; APPROVED) (DRAWERS: Action logs, Connection logs, Connections, Reports, Templates) | as listed |

**Decided with the user 2026-11-16:** Prefs editors = their own glass object + the blue gear emblem
(EmPrefs) lower right; Utilities and System programs = their own glass object, no emblem; selected
image = a moving part per object (decided one by one, like the drawers and files). First batch: the ten
most visible programs, then the Prefs editors.

First batch, APPROVED 2026-11-16 (docs/iconsets/glass/programs.png, programs_flip.gif, programs/PR*.png):

| ID | Program | Glass object | Selected |
|---|---|---|---|
| PR01 | Shell | a terminal: a glass screen block with a glowing `>_` prompt | the cursor jumps to a new line under a typed command (APPROVED) |
| PR02 | MultiView | a glass eye (lens + iris) in a ring, lids of black glass (user) | the lids open wide (APPROVED) |
| PR03 | NotePad | a glass note pad with lines and a pen lying on it | the pen stands at the start of the first line, starting to write (user) (APPROVED) |
| PR04 | Clock | a glass alarm clock with glowing hands, 10:10:00 | the hands move on to 10:40:30 (APPROVED) |
| PR05 | Calculator | a glass calculator, key grid and display ("30") | the = key pressed down, the display shows "42" (APPROVED) |
| PR06 | Find | a magnifying glass lying over a small page | it lifts and tilts towards the viewer (APPROVED) |
| PR07 | Format | a glass drive with a floppy half inserted | the floppy slides in (KEPT as is, user) |
| PR08 | Help | a closed glass book with a glowing `?` on its cover | the cover opens 30 degrees, book centred (user) (APPROVED) |
| PR09 | IconEdit | a glass grid of pixels with a glowing pencil | the pencil moves, one more pixel lit (APPROVED) |
| PR10 | UnArc | the open glass crate (AR01), lid thrown back | a small crate rises out of it (APPROVED) |

Prefs editors, ALL APPROVED 2026-11-16 (sheets docs/iconsets/glass/prefs1-4.png + _flip.gif, per editor programs/PF*.png); PF18 Presets is a drawer (each its own glass object + the blue gear emblem lower right, so the
moving part stays clear of the lower right; related editors share a base: printers, monitors, plugs):

| ID | Editor | Glass object | Selected |
|---|---|---|---|
| PF01 | AHI | an audio mixer with three faders | one fader slides up (APPROVED) |
| PF02 | AmigaInput | a joystick with a fire button | the stick tilts 13 degrees to the right (user) (APPROVED) |
| PF03 | ASL | a requester window with a file list and an OK button | the selection bar moves down a row (APPROVED) |
| PF04 | Compatibility | two glass puzzle pieces (old and new) | they slide together (APPROVED) |
| PF05 | Console | a small window with a prompt and a size gadget | LIST typed at the prompt, about to be sent; window size unchanged (user) (APPROVED) |
| PF06 | DefIcons | a card index with tabbed cards | one card pops up (APPROVED) |
| PF07 | DOS | a disk platter with a read/write arm, under a clear glass cover (user) | the arm swings over the platter (APPROVED) |
| PF08 | Font | a letterpress type block with a raised A | the block lifts straight up, no tilt (user) (APPROVED) |
| PF09 | GUI | a window with a slider and a checkbox | the slider knob slides across (APPROVED) |
| PF10 | Input | a two-button mouse | the left button clicks down (APPROVED) |
| PF11 | Internet | a small antenna mast with signal rings | the antenna telescopes up (APPROVED) |
| PF12 | Locale | a flag on a pole on a small base | the flag rises up the pole (APPROVED) |
| PF13 | Notifications | a bell on a stand | the bell swings, its clapper out (APPROVED) |
| PF14 | Palette | a painter's palette with glowing wells, a brush | the brush dips into a well (APPROVED) |
| PF15 | Picasso96Mode | a graphics card with a fan and a port | a monitor plug slides into the port (APPROVED) |
| PF16 | Pointer | a 3D mouse pointer arrow over a pad | the arrow presses down, a click ring lights (APPROVED) |
| PF17 | PopupMenu | a menu panel with items | a submenu pops out to the side (APPROVED) |
| PF18 | Presets | a DRAWER (user): the glass drawer + the swatch-fan emblem EmPresets, blue (docs/iconsets/glass/presets_drawer.png, PF18B) | the drawer opens (APPROVED) |
| PF19 | Printer | a printer, a text page in its slot | the page comes out of the top (APPROVED) |
| PF20 | PrinterGfx | the printer, a picture page; printed only above the print line, the part inside blank (user, applies to PF19-PF21) | the page comes out (APPROVED) |
| PF21 | PrinterPS | the printer, a page with a vector curve and handles | the page comes out (APPROVED) |
| PF22 | ScreenBlanker | a monitor with stars and a crescent moon | the moon moves across (APPROVED) |
| PF23 | ScreenMode | a monitor with a resolution frame inside | the frame grows to the screen's edges (APPROVED) |
| PF24 | Screens | two screens inside the glass monitor (user), one in front of the other | the front screen is dragged down (the Amiga screen drag), cut off at the bottom of the display; normal shows only that screen (user) (APPROVED) |
| PF25 | Serial | the Amiga serial port: 25-pin male D-sub on the computer side, the female D-sub on the cable (user) | the plug goes in (APPROVED) |
| PF26 | Sound | a loudspeaker (stays exactly still, user) | the cone pushes out, a ring of sound (APPROVED) |
| PF27 | Time | a digital alarm clock (user: time is better a clock), black glass display, 12:00 | another time (07:30) and lit from within (APPROVED) |
| PF28 | Timezone | a globe with a glowing time band | the band turns (APPROVED) |
| PF29 | UBoot | a small rocket on a launch pad (boot = launch) | the rocket lifts off (APPROVED) |
| PF30 | Updates | a tray with a download arrow above it | the arrow drops into the tray (APPROVED) |
| PF31 | URL | two chain links | the links close together (APPROVED) |
| PF32 | USB | a USB plug with the trident and its socket (USB-A, authentic) | the plug goes in (APPROVED) |
| PF33 | WBPattern | a paint roller on a patterned wall | the roller rolls on, more pattern (APPROVED) |
| PF34 | WBStartup | an illuminated rocker switch (user example: black housing, bezel, side latches, no contacts), I and O | rocked on, lit from within (APPROVED) |
| PF35 | Workbench | the Amiga desktop (user): a widescreen glass monitor showing the booted OS 4.1 Workbench as on the guest (title bar, drive icons top left, AmiDock right; no Boing ball, user) | windows open on it, spread out (System drawer upper right, Shell lower left, inside the display); monitor still (one framing for both images) (APPROVED) |

Made in batches of about nine, reviewed one by one.

Utilities and System, ALL APPROVED 2026-11-16 (checked against the inventory: all programs; no emblem; sheets docs/iconsets/glass/utils1-3.png + _flip.gif, per program programs/UT*.png, SY*.png):

| ID | Program | Glass object | Selected |
|---|---|---|---|
| UT01 | FileCompare | a balance with a page on each pan | the beam tips: they differ (APPROVED) |
| UT02 | GraphicDump | the printer (PF19), a page showing a screen grab | the page comes out (APPROVED) |
| UT03 | InitPrinter | the printer, its print head on a rail seen through the glass | the head returns to its start (APPROVED) |
| UT04 | Installation Utility | a glass software box, flaps closed | the flaps open, a glowing disc inside (APPROVED) |
| UT05 | KeyShow | a glass keyboard section | a key pressed down and lit (APPROVED) |
| UT06 | LogViewer | a glass scroll with lines | it unrolls further, more lines (APPROVED) |
| UT07 | MEmacs | a glass page of text with a glowing text cursor | the cursor moves on a line, the line typed (APPROVED) |
| UT08 | PartitionWizard | a disk drawn as a glass pie of partitions | one wedge slides out (APPROVED) |
| UT09 | PlayCD | a round top-loading glass CD player | its lid opens, the disc inside (APPROVED) |
| UT10 | PrefsObjectsEditor | a glass tree of nodes | a branch opens, its children slide out (APPROVED) |
| UT11 | PrintFiles | the printer, a file page (the G05 page) in its input tray | the page feeds in (APPROVED) |
| UT12 | RawDisk | a glass platter lying flat on the floor (user: standing it looked like a fan), an irregular disk layout (staggered sectors, used blocks lit, partitions; user: a regular grid looked like a fan grille) | one sector block lifts straight up out (APPROVED) |
| UT13 | ShowConfig | a stack of hardware: board, chip, cooler | the stack opens up (an exploded view) (APPROVED) |
| UT14 | USBInspector | the USB plug (PF32) with a magnifier | the magnifier moves over the trident (APPROVED) |
| SY01 | BIOSUpdater | a glass flash chip with its pins, an arrow above | the arrow drops into the chip (APPROVED) |
| SY02 | FixFonts | three type blocks in a row, one askew | the askew one snaps into line (APPROVED) |
| SY03 | FormatCDRW | a glass drive, a disc on its tray out (Format's family) | the tray slides in (APPROVED) |
| SY04 | GrimReaper | the Guru Meditation alert (user: another object than the scythe): a black glass panel on a stand, frame and two lines of text | the frame blinks on (lit) (APPROVED) |
| SY05 | Mounter | a glass drive in front of a drive bay | it slides into the bay (APPROVED) |
| SY06 | RexxMast | a glass crown on a cushion (the master of ARexx) | the crown lifts, glowing (APPROVED) |
| SY07 | RinghioServer | the PF35 monitor with the Workbench (user), a notification at the top right | two notifications (APPROVED) |
| SY08 | TypeManager | a type case with compartments of letter blocks | a letter block lifts out (APPROVED) |
| SY09 | Media Toolbox | a drive being worked on (user: a device and partition manager): a glass hard drive with its partition map on top, a wrench gripping a partition boundary | the wrench pushes the boundary, the first partition grows (APPROVED) |

This is the biggest group (about 80 own images). Could start with the most visible ones (Shell,
MultiView, NotePad, Clock, Calculator, Format, Find, the Prefs editors) and leave the rest native.

### 5. Emblems

About 20 glass tiles in deep red, green, blue and violet: music,
picture, video, text, document, guide, code, font, internet, mail, games, prefs, tools, system,
storage, devices, startup, download, archive, star, lock, check, warning, home. Final list follows
groups 1-4.

### 6. Left alone (C)

45 mouse pointers (`def_*pointer`), frames (`def_pictureframe`, `def_previewframe`, `def_textframe`),
overlays (`icon_leftout`, `icon_noaccess`, `icon_nodrop`), `def_iconify`, `def_window`, the docky icons
(`def_docky`, `def_extras_dock`, `def_internet_dock`, `def_players_dock`), `def_play`, `def_kingcon`.

## Selected states

Every base gets a lit selected image: the drawer opens, others glow from inside.

## How it is installed

**Decided by the user 2026-11-16:** the Emblem installer installs ONLY the plugin (emblem.iconmodule,
EmblemIcon, settings, documentation). The glass icon set gets an installation script of its own: it
needs the plugin, copies the set's images, converts the system's icons to Emblem icons after a backup,
and its remove restores the backed-up originals.
- The plugin keeps only a SMALL sample set (for its examples), with a script to remove the samples so
  the user can clear the system of them. **Done (2026-11-16, commit 887e198):** the package ships the 11
  images its examples use (`tools/make_examples.py --images`: DrawerNS/S + 9 emblems; was 21);
  `package/Emblem/RemoveSamples` (AmigaDOS, IconX icon P13, installed with the documentation) deletes
  the samples of this and every earlier version from ENVARC:/ENV:sys/emblem and nothing else (asks
  first; QUIET for Install's Remove, which now runs it); `tools/make_lha.sh` stops if it misses a shipped
  sample. Guest test: tests/os4/run_os4.py --step=6, 101/101 (2026-11-16); the double-click run (IconX window, y and n) checked by hand.
- Two archives: the plugin, and the icon set (each updated on its own).
- REVERT (the user, 2026-11-16: "I will be testing the new icon set in a live system I will want a way
  to revert the change once it is installed"): before changing anything the icon set installer copies
  every icon it will change, byte for byte, into a backup drawer with a manifest (original path +
  checksum), verified before any conversion; the backup drawer carries its own plain AmigaDOS restore
  script (works without the plugin and without Installer, from a Shell); the Installer remove does the
  same and removes the set's images and settings; ENVARC:Sys is restored and the ENV:Sys copies cleared;
  the restore checks every file against the manifest's checksums and names any mismatch; a second install
  never overwrites the first backup. Tested in the guest (install, restore, compare every file) before the
  user's live system.
- Names still to decide (the user will work them out separately): what the new icon type is called
  (today "Emblem": the module emblem.iconmodule, EMBLEM= settings) and what the icon set is called
  (working name "glass").

### The icon set's installer (design, 2026-11-16)

Names (decided 2026-11-17, see "Names" below; until then working names `glass`, `GlassIcons`,
`SYS:GlassIconsBackup`), each in one place in `tools/iconset_build.py`: images `ENVARC:sys/emblem/glenz/`,
package drawer `Glenz`, archive `dist/emblem_icons_glenz.lha`, backup drawer `SYS:GlenzBackup`.

- **Needs:** emblem.iconmodule running (installed + restarted: EmblemIcon can only write Emblem icons
  then), C:EmblemIcon 1.1 or newer (SET), C:MD5Sum (part of OS 4.1 FE: `MD5Sum ... >>list`,
  `MD5Sum CHECK=list STATUS` gives 5 on any changed or missing file). Missing → stops, changes nothing.
- **Backup first** (`Scripts/Backup`, generated from the mapping): every mapped icon that exists is copied
  with `Copy CLONE` into `SYS:GlenzBackup/files/<root>/<path>` (root SYS or ENVARC; ENVARC:Sys def_
  icons and ENVARC:sys/emblem.prefs), and its MD5 goes into `<root>.md5` with the name relative to the
  root, so one list checks the originals (CD SYS:) and the copies (CD files/SYS). An icon already in the
  backup is never copied again: an update keeps the first backup and only adds icons new to the set.
- **Checked before any change** (`Scripts/Verify`): every copy against its list, and every original
  saved in this run against the same list. Any difference → stop, nothing changed.
- **Then:** the marker `Installed` and the `Restore` script (+ icon) go into the backup drawer; the images
  are copied; the emblem shadow the set was drawn with (SHADOWOFFSET=2,2, SHADOWBLUR=2, SHADOWOPACITY=55)
  is added to ENVARC:/ENV:sys/emblem.prefs (saved first; asked, default yes); the emblem settings say
  SHADOW, so the set looks as approved whatever EMBLEMMETHOD says; `Scripts/Convert` (generated) turns
  every BACKED-UP icon into an Emblem icon with `EmblemIcon ... TO=EMBLEM SET="..."` and copies the
  changed def_ icons to ENV:Sys. Failures are listed; the backup and Restore are already in place.
- **Restore** (`SYS:GlenzBackup/Restore`, plain AmigaDOS: no plugin, no Installer; double-click it
  (IconX, asks first) or `Execute SYS:GlenzBackup/Restore [QUIET]`): checks the copies against the
  lists (any change → restores nothing and names the files), copies them back with `Copy ALL CLONE`
  (ENVARC files also to ENV:), checks every restored file against the lists and names any mismatch;
  on success deletes the marker. The images stay (Install → Remove deletes them).
- **Install again:** with the marker = update (backup kept, new icons added). Without it (the set was
  restored) an old backup is renamed `SYS:GlenzBackup.old` (replacing an older .old) and a fresh one
  is made, so a backup is never mixed with icons changed after a restore.
- **Remove** (Install): runs Restore QUIET; only when it succeeds deletes the images (ENVARC: and ENV:).
  The backup drawer stays until the user deletes it.
- **Built and tested 2026-11-16, again with the final names 2026-11-17 (64/64):** `tools/iconset_build.py package` → dist/emblem_icons_glenz.lha (230 files,
  1.3 MB; package/iconset/README.md). Guest cycle `tests/os4/run_iconset.py`: 60/60 — 233 files saved
  (MD5 + date + protection + comment equal), 232 icons become Emblem icons (10 → 242 in SYS:), 7 composed
  exactly like the host renders, update keeps the backup, Restore and Remove put every file back exactly
  (also the ENV: copies), install after Restore keeps the old backup as .old. Install takes ~45 s.
  Double-click Restore (IconX, y) checked by hand. Screenshot: build/os4-qemu/iconset_installed.png.

Earlier notes:


- Default images and emblems go to ENVARC:sys/emblem as now.
- Install converts the chosen icons to Emblem icons with their settings (EmblemIcon), after a backup.
- Remove converts them back and restores the backup, so the user's own icons are never lost.

## The stock icons not mapped yet (user, 2026-11-17)

Went through the 546 unmapped stock icons by drawer (the decisions live in `tools/iconset_build.py`,
the lists in docs/iconset_mapping.md):
- Everything below SYS:Emulation stays classic; only its two drawer icons (AmigaDisks, AmigaROMs, already
  in the set) get the set.
- Icons in a drawer that has no icon itself are left alone (55).
- **To do (31):** SYS:ChangeLog.guide, the six drawers in SYS:Prefs/Presets, SYS:System/AmiUpdate
  (AmiUpdate, System_RollBack), SYS:System/Python (Lib, Python), AmiGS, AmiPDF, the 16 commodities,
  SGrab and its guide.
- **Not needed (58):** SYS:Documentation's SFTPHandler drawer and files, AmiSSL docs, the MiniGL demos,
  SYS:Prefs/sftphprefs.
- **Set aside for now (263):** DataTypes, DOSDrivers, monitors and printers (Devs and Storage), MUI and its
  demos/docs, the Presets' AmiDock/Default/SilverGreen contents, NetInterfaces, Blankers, Dockies.
- **The PDF swirl** on the AmiPDF and AmiGS emblems stays (user, 2026-11-17): the stock OS 4.1 icons and
  free PDF icons all use a swirl of their own; ours is a free drawing of that idea. Not an open question
  any more; the AmiPDF/AmiGS program icons (to do) keep it too.

## Names (user, 2026-11-17)

- Plugin archive **emblem_icons.lha** (the small sample set and the tools); the set's archive
  **emblem_icons_glenz.lha**; the set is called **Glenz**: drawer `Glenz` in its archive, images in
  `ENVARC:sys/emblem/glenz/`, backup drawer `SYS:GlenzBackup` (each name in one place in
  `tools/iconset_build.py`; the plugin archive's in `tools/make_lha.sh`).
- **Open issue:** the images in their own drawer (`glenz/`) or directly in `ENVARC:sys/emblem`. For the
  drawer: no name clashes with the user's own images or the samples, Install/Remove replace or delete
  just that drawer, several sets can sit side by side, and a setting says where its image comes from
  (`IMAGE=glenz/p_printer`). Against: a few more characters per setting. Changing it is the `SET` name.

## The "do" icons (user, 2026-11-21)

- **Commodities (16):** each its own glass object (like the Prefs editors) + a new violet family
  emblem lower right: a keycap with the Amiga "A" (the stock OS 4.1 family mark); selected = a moving
  part per object.
- **Everything else is decided one icon at a time** (user: "Let's do these one by one"): the six
  Presets sub-drawers (glass drawer + a blue emblem), Python/Lib (drawer + red emblem), the programs
  AmiUpdate, System_RollBack, AmiGS, AmiPDF, SGrab, the Python icon, and the two guides.
  Sheets in docs/iconsets/glass/do/ (IDs DO01...; variants A, B, C until one is picked).
- DO01 Presets/AmiDock: variants A (dock bar with three icons), B (upright dock), C (dock bar, the
  middle icon zoomed up), docs/iconsets/glass/do/do01_amidock.png. **PICKED: A** (tile SdPrAmiDock).
- DO02 Presets/Default (holds the GUI looks per screen size): A star, B monitor showing a window,
  C window with a check mark, docs/iconsets/glass/do/do02_default.png. **PICKED: B** (tile SdPrDefault).
- DO03 Presets/Patterns: A the MUI/Patterns checker tile (SdMuiPatterns), B a wallpaper of diamonds,
  C a wallpaper roll with the patterned sheet hanging down, docs/iconsets/glass/do/do03_patterns.png.
  **PICKED: A** (the same tile as MUI/Patterns, SdMuiPatterns).
- DO04 Presets/Pointers: A the pointer arrow, B the arrow + the busy clock, C three arrows,
  docs/iconsets/glass/do/do04_pointers.png. **PICKED: A** (tile SdPrPointers).
- DO05 Presets/SilverGreen (a theme): A Default's monitor + a paint brush, B a window + a paint brush,
  C the letters SG, docs/iconsets/glass/do/do05_silvergreen.png. **PICKED: A** (tile SdPrSilverGreen).
- DO06 Presets/Sounds: A a loudspeaker with two waves, B a music note (the EmMusic symbol, blue),
  C a waveform, docs/iconsets/glass/do/do06_sounds.png. **PICKED: C** (tile SdPrSounds).
- DO07 System/Python/Lib (red, System's colour): A the MUI/Libs book spines, B three stacked
  building blocks (modules), C the letters py, docs/iconsets/glass/do/do07_pylib.png. **PICKED: C**
  (tile SdPyLib).
- DO08 System/AmiUpdate/AmiUpdate (own glass object, the drawer emblem's gear, tools/blender/glass_do.py):
  A gear + red button, selected: the button pressed in and brighter; B the same, selected: the gear
  turns half a tooth; C gear + a glowing red down arrow, selected: the arrow drops;
  docs/iconsets/glass/do/do08_amiupdate.png. **PICKED: A** (ICON amiupdate).
- DO09 System/AmiUpdate/System_RollBack (own glass object): A a glass clock in a green back-arrow ring,
  selected: the hands go back an hour; B the same, selected: the arrow ring turns back; C AmiUpdate's
  gear with a green back arrow, selected: the arrow turns back; docs/iconsets/glass/do/do09_rollback.png.
  **PICKED: C** (ICON rollback).
- DO10 Utilities/AmiGS/AmiGS (own glass object: the drawer emblem's white page, red swirl, PS, magnifier):
  A selected: the magnifier lifts and tilts towards the viewer; B selected: it slides over the swirl;
  docs/iconsets/glass/do/do10_amigs.png. **PICKED: A**, the page stays white (ICON amigs).
- DO11 Utilities/AmiPDF/AmiPDF: the same as AmiGS with PDF (ICON amipdf); docs/iconsets/glass/do/do11_viewers.png.
- DO12 SGrab: the drawer emblem's glass camera, standing; sheet do12_sgrab. **PICKED A** (2026-11-22): selected = the button pressed in (red) and the flash fires (dim grey-blue when not).
- DO13 System/Python/Python (icon): the drawer emblem's Boing ball + yellow ring, standing; sheet do13_python. **PICKED A** (2026-11-22): selected = the ball turns (the checks move on).
- SYS:ChangeLog.guide and SYS:Utilities/SGrab/SGrab.guide (user 2026-11-22): the def_guide icon (glass file page + EmDocs), no new art.
- DO14 the commodities' family emblem (violet, lower right): the Amiga key's "A" (slanted, thin left and thick right stroke, serifs; drawn after the stock keycaps, user 2026-11-22) on a keycap; variants A (3D keycap outline), B (solid keycap, A cut out), C (face + skirt), sheet do14_commodity_emblem. **PICKED B** (tile EmCommodity).
- CO01 Commodities/AmiDock (+ EmCommodity): A glass dock bar with three icons (selected: the middle one pops up), B the stock icon's red button on a glass base (pressed, lit), C upright dock (top icon slides out); sheet co01_amidock. **PICKED A** (2026-11-22).
- CO02 Commodities/AsyncWB: A two windows + a green busy spinner (selected: turns on, lit), B window with a progress bar (fills), C two windows and a page between them (page arrives); sheet co02_asyncwb. **PICKED A** (2026-11-22).
- CO03 Commodities/AutoBorderSize (resize windows by catching the border; user 2026-11-23: the arrows by the border): A double arrow on the left border (window wider), B diagonal arrow on the upper right corner (bigger), C as A + the caught border lit blue (arrows kept off the lower right, the emblem's place); sheet co03_autobordersize. **PICKED C** (2026-11-23).
- CO04 Commodities/AutoInfo: A page icon + yellow info card (pops up, lit), B glass info sign (the i's dot hops up), C pointer on a page icon (info card slides out); sheet co04_autoinfo. **PICKED A** (2026-11-23).
- CO05 Commodities/AutoPoint: A two windows, pointer on the back one (its title lights), B pointer moves onto a window (title lights), C as A + the back window comes forward; sheet co05_autopoint. **PICKED C** (2026-11-23).
- CO06 Commodities/ClickToFront (the window you click on comes to the front): A two windows + pointer with double-click rings (back one comes to the front), B the windows swap, C three stacked windows (the rearmost comes to the front); sheet co06_clicktofront. **PICKED A** (2026-11-23).
- CO07 Commodities/ContextMenus: A window + glass pop-up menu, an item lit under the pointer (next item lit), B the menu pops up at the pointer, C a lit item's submenu slides out; sheet co07_contextmenus. **PICKED A** (2026-11-23).
- CO08 Commodities/CrossDOS (reads and writes PC disks): A the glass floppy (shutter opens), B a page rises out of it, C a blue two-way arrow across it (lights up); sheet co08_crossdos. **PICKED A** (2026-11-23).
- CO09 Commodities/DefIcons (files without an icon get one by their type): A three glass pages with type marks (text, sound, picture; fan out), B a plain page that gets a picture, C a stack whose front page lifts; sheet co09_deficons. **PICKED A** (2026-11-23).
- CO10 Commodities/DepthToFront (the depth gadget brings a window to the front): A two windows, the pointer on the back one's depth gadget (it comes to the front), B a large glass depth gadget (back square forward), C the windows swap; sheet co10_depthtofront. **PICKED A** (2026-11-23).
- CO11 Commodities/Exchange (turns the commodities on and off, shows and quits them): A a panel with three switches (one switched off), B a glass dot display with CX in green dots (letters scroll one dot), C a list window (a row selected, its light off); sheet co11_exchange. **PICKED B** (2026-11-23).
- CO12 Commodities/FKey (keys that start programs and do other actions): A a glass F1 key on a slab (pressed, face blue), B three keys F1-F3 (middle pressed), C the key and a window that pops up; sheet co12_fkey. **PICKED A** (2026-11-23).
- CO13 Commodities/MouseBlanker (hides the pointer while you type): A a window with the pointer (fades to an outline), B the pointer over glass keys (a key down, pointer fades), C a window with text and a blue text cursor (more text typed, pointer fades); sheet co13_mouseblanker. **PICKED C** (2026-11-23).
- CO14 Commodities/NoCapsLock (Caps Lock does nothing): A the glass Caps Lock key with the stock arrow and a green light (pressed, light out), B a red no-sign in front (pressed, sign lit), C a capital A (pressed, a small a); sheet co14_nocapslock. **PICKED A** (2026-11-23).
- CO15 Commodities/RAWBInfo (Workbench's Information window, made with ReAction): A a window with the glass info sign (comes forward), B a page whose Information window pops up, C an Information window with the info sign and three fields (the first lit, edited); sheet co15_rawbinfo. **PICKED C** (2026-11-23).
- CO16 Commodities/ScreenBlankerEngine (blanks the screen when the computer is left alone): A a glass monitor with an amber roller blind half down (pulled down), B the screen blanked with stars, C blanked with stars and a Zz; sheet co16_screenblankerengine. **PICKED A** (2026-11-23).
