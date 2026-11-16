#!/bin/bash
# Puts the release together and packs it: dist/Emblem.lha and dist/Emblem.readme
#
#   make os4 tools && tools/make_lha.sh
#
# Layout of the archive:
#   Emblem.info, Emblem.readme
#   Emblem/                          drawer
#     Install                        Installation Utility script (install, update, remove)
#     RemoveSamples                  AmigaDOS script: deletes the sample images (installed
#                                    with the documentation; Install's Remove runs it too)
#     Emblem.guide                   documentation
#     LICENSE.txt, Emblem-format.txt
#     Libs/IconModules/emblem.iconmodule
#     C/EmblemIcon
#     Images/*.png                   the sample images: only those the examples use
#                                    (tools/make_examples.py --images; art/, tools/make_art.py)
#     Examples/                      Emblem icons (tools/make_examples.py) + ReadMe
#
# The LHA and the readme are also copied to $RELEASES (default: the shared
# folder's releases/), when that folder exists.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LHA="${LHA:-$HOME/linux_archivers/lha/lha}"
RELEASES="${RELEASES:-/media/sf_claude_folder/releases}"
STAGE="$ROOT/build/stage"
OUT="$ROOT/dist/Emblem.lha"
REV="$ROOT/src/emblem.iconmodule_rev.h"

ver=$(sed -n 's/^#define VERSION *\([0-9]*\)/\1/p' "$REV").$(sed -n 's/^#define REVISION *\([0-9]*\)/\1/p' "$REV")
amigadate=$(sed -n 's/^#define DATE *"\(.*\)"/\1/p' "$REV")
isodate=$(date +%Y%m%d)

for f in "emblem.iconmodule:emblem.iconmodule $ver ($amigadate)" "EmblemIcon:EmblemIcon "; do
	bin="$ROOT/build/os4/${f%%:*}"
	if ! strings "$bin" | grep -qF "${f#*:}"; then
		echo "$bin is not \"${f#*:}\"; run make os4" >&2
		exit 1
	fi
done
[ -x "$ROOT/build/host/mkemblem" ] || { echo "build/host/mkemblem missing; run make tools" >&2; exit 1; }

# every release says what changed
grep -q "^- $ver (" "$ROOT/package/Emblem.readme" ||
	{ echo "package/Emblem.readme has no History entry \"- $ver (...)\"" >&2; exit 1; }
grep -q "^@{b}$ver (" "$ROOT/package/Emblem/Emblem.guide" ||
	{ echo "Emblem.guide has no History entry for $ver" >&2; exit 1; }

rm -rf "$STAGE"
D="$STAGE/Emblem"
mkdir -p "$D/C" "$D/Libs/IconModules" "$D/Images" "$ROOT/dist"

cp "$ROOT/build/os4/emblem.iconmodule" "$D/Libs/IconModules/"
cp "$ROOT/build/os4/EmblemIcon" "$D/C/"
# the small sample set: the images the examples use. RemoveSamples must know
# every one of them (its list also keeps the names of earlier versions' samples)
samples=$("$ROOT/tools/make_examples.py" --images)
for n in $samples; do
	cp "$ROOT/art/$n.png" "$D/Images/"
	grep -q "[(|]$n[|)]" "$ROOT/package/Emblem/RemoveSamples" ||
		{ echo "package/Emblem/RemoveSamples does not delete the sample $n" >&2; exit 1; }
done
cp "$ROOT/package/Emblem/Install" "$ROOT/package/Emblem/RemoveSamples" "$D/"
sed -e "s/^@\$VER: Emblem.guide [0-9.]* ([0-9.]*)/@\$VER: Emblem.guide $ver ($amigadate)/" \
	"$ROOT/package/Emblem/Emblem.guide" | iconv -f UTF-8 -t ISO-8859-1 > "$D/Emblem.guide"
cp "$ROOT/UNLICENSE" "$D/LICENSE.txt"
iconv -f UTF-8 -t ISO-8859-1 "$ROOT/docs/format.md" > "$D/Emblem-format.txt"
sed -e "s/@VERSION@/$ver/" -e "s/@DATE@/$isodate/" "$ROOT/package/Emblem.readme" |
	iconv -f UTF-8 -t ISO-8859-1 > "$STAGE/Emblem.readme"

"$ROOT/tools/make_examples.py" "$ROOT/art" "$D/Examples"
iconv -f UTF-8 -t ISO-8859-1 "$ROOT/package/Emblem/Examples/ReadMe" > "$D/Examples/ReadMe"

# native icons made by icon.library itself, see package/icons/README.md;
# "_" in their names stands for "/"
I="$ROOT/package/icons"
cp "$I/Emblem.info" "$STAGE/"
for f in "$I"/*.info; do
	n=$(basename "$f")
	[ "$n" = Emblem.info ] && continue
	cp "$f" "$D/${n//_//}"
done

rm -f "$OUT"
(cd "$STAGE" && "$LHA" aq2o5 "$OUT" Emblem.info Emblem.readme Emblem)
"$LHA" l "$OUT" | tail -3
cp "$STAGE/Emblem.readme" "$ROOT/dist/"
echo "version $ver -> $OUT"
if [ -d "$RELEASES" ]; then
	cp -p "$OUT" "$STAGE/Emblem.readme" "$RELEASES/"
	echo "copied LHA and readme to $RELEASES"
else
	echo "note: $RELEASES not found, nothing copied" >&2
fi
