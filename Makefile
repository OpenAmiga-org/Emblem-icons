# Emblem icon plugin
#   make test   host tests: file format, PNG decoder, tool types (ASan/UBSan, zlib, pypng)
#   make os4    cross-build module, EmblemIcon and the guest test helper (walkero docker)

DOCKER_IMAGE = walkero/amigagccondocker:os4-gcc15-3.7.0
OS4 = build/os4
HOST = build/host

.PHONY: all test tools os4 os4-profile os4-profile-in-docker os4-in-docker clean

all: test os4

PYTHON = $(HOME)/build/emblem-venv/bin/python
SAN = -std=c99 -D_DEFAULT_SOURCE -Wall -Wextra -g -O1 -fsanitize=address,undefined -fno-sanitize-recover=undefined

test: $(HOST)/test_emblemfile $(HOST)/test_png $(HOST)/test_spec $(HOST)/test_compose $(HOST)/render build/pngref/.done
	$(HOST)/test_emblemfile
	$(HOST)/test_png tests/samples/pngsuite build/pngref
	$(HOST)/test_spec
	$(HOST)/test_compose

$(HOST)/test_emblemfile: tests/host/test_emblemfile.c src/emblemfile.c src/emblemfile.h
	@mkdir -p $(HOST)
	gcc $(SAN) -o $@ tests/host/test_emblemfile.c src/emblemfile.c -lz

$(HOST)/test_png: tests/host/test_png.c src/png.c src/png.h
	@mkdir -p $(HOST)
	gcc $(SAN) -o $@ tests/host/test_png.c src/png.c -lz

$(HOST)/test_spec: tests/host/test_spec.c src/emblemspec.c src/emblemspec.h src/compose.c src/compose.h
	@mkdir -p $(HOST)
	gcc $(SAN) -o $@ tests/host/test_spec.c src/emblemspec.c src/compose.c

$(HOST)/test_compose: tests/host/test_compose.c src/compose.c src/compose.h src/emblemspec.c src/emblemspec.h src/emblemprefs.c src/emblemprefs.h
	@mkdir -p $(HOST)
	gcc $(SAN) -o $@ tests/host/test_compose.c src/compose.c src/emblemspec.c src/emblemprefs.c

# host tool for the package: writes Emblem icons (the example icons)
tools: $(HOST)/mkemblem

$(HOST)/mkemblem: tools/mkemblem.c src/emblemfile.c src/emblemfile.h src/png.c src/png.h
	@mkdir -p $(HOST)
	gcc $(SAN) -o $@ tools/mkemblem.c src/emblemfile.c src/png.c -lz

# host renderer: the module's composition on the host (golden renders, guest test expectations)
$(HOST)/render: tests/host/render.c src/compose.c src/compose.h src/emblemspec.c src/png.c src/png.h src/emblemprefs.c src/emblemprefs.h
	@mkdir -p $(HOST)
	gcc -std=c99 -D_DEFAULT_SOURCE -Wall -Wextra -O2 -o $@ tests/host/render.c src/compose.c src/emblemspec.c src/png.c src/emblemprefs.c -lz

# reference pixels for the PNG test, made with pypng (venv: python3 -m venv ~/build/emblem-venv; pip install pypng)
build/pngref/.done: tests/host/make_png_refs.py
	$(PYTHON) tests/host/make_png_refs.py
	touch $@

# a module that prints phase timings to the debug buffer (never shipped)
os4-profile:
	@mkdir -p $(OS4)
	sudo docker run --rm -u $$(id -u):$$(id -g) -v $(CURDIR):/src -w /src $(DOCKER_IMAGE) \
		make os4-profile-in-docker < /dev/null

os4-profile-in-docker:
	$(CC) $(MODFLAGS) -DEMBLEM_PROFILE -o $(OS4)/emblem.iconmodule.profile $(MODSRC) -lgcc

os4:
	@mkdir -p $(OS4)
	sudo docker run --rm -u $$(id -u):$$(id -g) -v $(CURDIR):/src -w /src $(DOCKER_IMAGE) \
		make os4-in-docker < /dev/null

# --- inside the docker ---
CC = ppc-amigaos-gcc
STRIP = ppc-amigaos-strip --strip-all -R .comment
# The module has no C library: -nostdlib, own memcpy/memset in module.c, libgcc for helpers.
MODFLAGS = -O2 -Wall -Wno-unused-parameter -fno-builtin -nostdlib -nostartfiles
TOOLFLAGS = -O2 -Wall -Wno-pointer-sign -D__USE_INLINE__

os4-in-docker: $(OS4)/emblem.iconmodule $(OS4)/EmblemIcon $(OS4)/EmblemInfo $(OS4)/icontest $(OS4)/memeater $(OS4)/mkicon

MODSRC = src/module.c src/emblemfile.c src/emblemspec.c src/compose.c src/imagecache.c src/png.c src/emblemprefs.c

$(OS4)/emblem.iconmodule: $(MODSRC) src/*.h
	$(CC) $(MODFLAGS) -o $@.debug $(MODSRC) -lgcc
	$(STRIP) -o $@ $@.debug

$(OS4)/EmblemIcon: src/emblemicon.c src/EmblemIcon_rev.h src/emblem.h
	$(CC) $(TOOLFLAGS) -o $@.debug src/emblemicon.c -lauto
	$(STRIP) -o $@ $@.debug

# EmblemInfo: the settings editor (ReAction)
$(OS4)/EmblemInfo: src/embleminfo.c src/EmblemInfo_rev.h src/emblem.h src/emblemspec.c src/emblemspec.h
	$(CC) $(TOOLFLAGS) -o $@.debug src/embleminfo.c src/emblemspec.c -lauto
	$(STRIP) -o $@ $@.debug

$(OS4)/icontest: tests/os4/icontest.c src/emblem.h src/compose.c src/compose.h
	$(CC) $(TOOLFLAGS) -o $@ tests/os4/icontest.c src/compose.c -lauto

$(OS4)/memeater: tests/os4/memeater.c
	$(CC) -O2 -Wall -o $@ tests/os4/memeater.c -lauto

# guest helper that saves the package's native icons (tools/make_art.py, package/icons)
$(OS4)/mkicon: tools/os4/mkicon.c
	$(CC) -O2 -Wall -o $@ $< -lauto

clean:
	rm -rf build
