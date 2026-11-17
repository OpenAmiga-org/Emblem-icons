# Emblem icon file format, version 1

An Emblem icon is a `.info` file that `emblem.iconmodule` reads and writes. It carries everything a
`struct DiskObject` holds plus the icon's own images, so converting back to a native Amiga icon loses
nothing. The icon's Emblem settings (default images and emblems: `IMAGE=`, `IMAGESELECTED=`,
`EMBLEM=`, `EMBLEMSELECTED=`) are kept in their own chunk, `ESET`, not in the tool types; the
module composes the displayed images from them when it loads the icon.

The file is an IFF FORM (big-endian, chunks padded to even length):

```
FORM <size> EMBL
  HEAD   always, first chunk (fixed position: file offset 12)
  DRAW   drawer data (only for icons that have it)
  DEFT   default tool
  TTYP   tool types
  ESET   the Emblem settings (module 1.1 and newer)
  TWIN   tool window
  IMAG   one per stored image (normal, selected)
  ....   unknown chunks: kept as they are when the module saves the icon
```

icon.library only asks modules about files that are not native icons and are at least 58 bytes long;
FORM + HEAD alone are 44 bytes, so the writer adds a `PAD ` chunk (zero bytes, ignored by readers)
when a file would be shorter (never in practice: every icon has an image).

## HEAD (24 bytes)

| Offset | Size | Field |
|---|---|---|
| 0 | u16 | format version (1) |
| 2 | u8 | `do_Type` (WBDISK..WBAPPICON) |
| 3 | u8 | flags: bit 0 frameless |
| 4 | u8 | aspect ratio (`PACK_ICON_ASPECT_RATIO`, 0 = unknown) |
| 5 | u8 | reserved, 0 |
| 6 | u16 | `do_Gadget.Flags` |
| 8 | u16 | `do_Gadget.Width` |
| 10 | u16 | `do_Gadget.Height` |
| 12 | i32 | `do_CurrentX` (NO_ICON_POSITION = 0x80000000) |
| 16 | i32 | `do_CurrentY` |
| 20 | i32 | `do_StackSize` |

`do_CurrentX` is at file offset 12 + 8 + 12 = 32, so a snapshot (`ICONPUTA_OnlyUpdatePosition`)
rewrites 8 bytes in place.

## DRAW (22 bytes)

| Offset | Size | Field |
|---|---|---|
| 0 | i16 x4 | `dd_NewWindow` LeftEdge, TopEdge, Width, Height |
| 8 | i32 | `dd_CurrentX` |
| 12 | i32 | `dd_CurrentY` |
| 16 | u32 | `dd_Flags` |
| 20 | u16 | `dd_ViewModes` |

The other NewWindow fields are not stored (Workbench builds its own window from the box).

## DEFT, TWIN

The string bytes, no terminating NUL (the chunk length is the string length).

## TTYP

Each tool type as a NUL-terminated string, one after the other. An empty chunk = no tool types.

## ESET

The icon's Emblem settings, packed like the tool types: each a NUL-terminated `KEY=value` string.
The module reads `IMAGE=Name[,Method]`, `IMAGESELECTED=`, `EMBLEM=Name[,W,H,X,Y,Method]` and
`EMBLEMSELECTED=` (src/emblemspec.h; the first of a key counts) and keeps every string, also others,
when it saves the icon. No chunk (or an empty one) = no settings.

They are not tool types because many programs read all of their icon's tool types as arguments
(`ReadArgs()` with the template of their command line): most OS 4 Prefs editors refuse to start when
an icon has a tool type their template doesn't know. Programs read and change the settings with the
`EMBLEMA_GetSettings` and `EMBLEMA_SetSettings` tags (src/emblem.h); `C:EmblemIcon SET=` and `UNSET=`
do it from the shell. Module 1.0 doesn't know this chunk: it kept it as an unknown chunk.

## IMAG

| Offset | Size | Field |
|---|---|---|
| 0 | u8 | state: 0 normal, 1 selected |
| 1 | u8 | kind: 1 ARGB, 2 CLUT, 3 planar |
| 2 | u8 | compression: 0 none, 1 zlib (z.library `Compress2`) |
| 3 | u8 | reserved, 0 |
| 4 | u16 | width |
| 6 | u16 | height |
| 8 | ... | kind header (below) |
| | u32 | uncompressed data length |
| | ... | data |

Kind headers and data:

- **ARGB** (`IDFMT_DIRECTMAPPED`): no header. Data: width x height longwords 0xAARRGGBB.
- **CLUT** (`IDFMT_PALETTEMAPPED`): u16 palette size (1..256), i16 transparent index (-1 = none),
  palette size x 3 bytes R, G, B. Data: width x height bytes.
- **Planar** (`IDFMT_BITMAPPED`, `struct Image`): i16 LeftEdge, i16 TopEdge, u16 Depth,
  u8 PlanePick, u8 PlaneOnOff. Data: Depth planes (as in native icon files), each height rows of
  ((width + 15) / 16) words. Width up to 1024 (old planar icons can be wider than 256).

Which images are stored depends on the icon's image data format: ARGB icons store ARGB images, CLUT
icons CLUT images, old icons their planar images. The selected image is stored only if the icon has a
real one (`ICONCTRLA_HasRealImage2`, or a `SelectRender` image for planar icons).

Chunky (ARGB/CLUT) icons may also carry **planar fallback** images: IMAG chunks of kind 3 next to the
chunky ones (state 0 and 1 again). Native icons have them (2 planes usually, 8 in some, e.g.
`SYS:Disk.info`), and icon.library needs one to duplicate an icon (`DupDiskObject`) or save it
natively. Rules:

- Converting a native icon stores its fallback as it is.
- An Emblem file without a fallback gets a 4-colour one built by the module at load time
  (pens 0 background, 1 black, 2 white, 3 blue by brightness); it is not written back.
- When the module saves a chunky icon it loaded itself, it writes back the fallback chunks and the
  gadget size from the file (kept with the icon), not `GadgetRender`: once Workbench has laid the
  icon out, `GadgetRender` holds an 8-plane copy remapped to that screen.

The parser keeps chunky and planar images apart: `EFIcon.img[]` and `EFIcon.planar[]`.
