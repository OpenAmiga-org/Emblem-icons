# The icon set's package

The glass icon set (working names: images `glass`, package `GlassIcons`, backup `SYS:GlassIconsBackup`;
each name in one place in `tools/iconset_build.py`) has its own archive, separate from the plugin:

    tools/iconset_build.py package        ->  dist/GlassIcons.lha (stage: build/stage-iconset)

| In the archive | From |
|---|---|
| `GlassIcons.info`, `GlassIcons/Install.info`, `GlassIcons/Icons/Restore.info` | `icons/` here (native icons, see below) |
| `GlassIcons/Install` | `Install` here, with the names and the icon count filled in |
| `GlassIcons/Images/glass/*.png` | the export (`iconset_build.py export`): 78 images x2 (64x64), 66 emblems (28x28) |
| `GlassIcons/Scripts/Backup`, `Convert` | generated from the mapping (one block per icon) |
| `GlassIcons/Scripts/Verify`, `Restore.body` | here |

What the Install does, and why, is in docs/iconset_plan.md ("The icon set's installer"): it saves every
icon it changes (and emblem.prefs) in the backup drawer with MD5 checksums (C:MD5Sum of OS 4.1 FE), checks
the copies, writes the standalone `Restore` script there, and only then copies the images and turns the
saved icons into Emblem icons. `Restore` needs neither the plugin nor the Installer.

The guest test of the whole cycle (install, update, Restore, install again, Remove; every file compared
by MD5, date, protection and comment) is `tests/os4/run_iconset.py`.

## The package's own icons

Native icons (they must show without the plugin), pictures composed from the set's images by the
module's engine:

1. `tools/iconset_build.py icons` writes `build/iconset/icons/*.argb` and `mkicons.script`.
2. Copy them with `build/os4/mkicon` to a drawer in the OS4 guest and run `Execute mkicons.script`.
3. Copy `out/*.info` here to `icons/`.
