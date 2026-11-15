# Package icons

These `.info` files were saved by AmigaOS 4's icon.library (native format,
64x64 true colour pictures, no planar picture): the package's own icons must
show before emblem.iconmodule is installed, and AmigaOS 4 does not read
PNG icons, so they cannot be written on the host. "_" in a name stands for
"/" (tools/make_lha.sh puts `C_EmblemIcon.info` at `C/EmblemIcon.info`).

The example icons in the package's Examples drawer are Emblem icons; they
are written on the host by `tools/make_examples.py` (build/host/mkemblem).

The pictures are drawn by `tools/make_art.py` (public domain, like the rest
of the project). To change an icon:

1. `tools/make_art.py art` writes `art/icons/*.argb` and
   `art/icons/mkicons.script` (and the art set itself).
2. `make os4` builds `build/os4/mkicon` (tools/os4/mkicon.c).
3. Copy mkicon, the `.argb` files and the script to a drawer in the OS4
   guest and run `Execute mkicons.script` there; the icons appear in `out/`.
4. Copy them back here.
