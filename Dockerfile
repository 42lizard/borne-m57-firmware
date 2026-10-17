# Multi-stage Dockerfile that compiles the borne m57 firmware to a .uf2.
#
# Build via the helper:
#   scripts/build.sh
#
# Or directly:
#   DOCKER_BUILDKIT=1 docker build --target export --output type=local,dest=build .
#
# Output: ./build/m57_via.uf2

# ---- builder ----
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# arm cross-toolchain + python + qmk cli (Makefile calls `qmk` during build).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        make \
        gcc-arm-none-eabi \
        binutils-arm-none-eabi \
        libnewlib-arm-none-eabi \
        python3 \
        python3-pip \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir qmk

# fetch vial-qmk at a pinned commit + init submodules. bump VIAL_QMK_REF
# deliberately, never implicitly: the LUKS fix overrides weak
# is_keyboard_master_impl and CHORDAL_HOLD is a rules.mk flag - both regress
# SILENTLY if upstream renames them. after a bump, re-run the flash-and-check
# list (todo.md) before trusting a build.
ARG VIAL_QMK_REF=00fc4627cd038ac9b7e9b8bf2b40b50e9e88aecb
RUN git init /vial-qmk \
 && cd /vial-qmk \
 && git remote add origin https://github.com/vial-kb/vial-qmk \
 && git fetch --depth 1 origin ${VIAL_QMK_REF} \
 && git checkout FETCH_HEAD \
 && git submodule update --init --recursive

# tell qmk to use vial-qmk as its source tree.
ENV QMK_HOME=/vial-qmk
RUN qmk config user.qmk_home=/vial-qmk

WORKDIR /vial-qmk

# drop the keyboard source in. AFTER submodule init so source edits don't bust the heavy layer.
COPY source/m57 keyboards/m57
# Vial uses BUILD_ID as EEPROM validity marker. Keep it stable until the
# storage schema changes, so compatible rebuilds preserve user edits.
COPY source/m57/build_id.py util/build_id.py
COPY scripts/vil_defaults_gen.py /tmp/vil_defaults_gen.py
COPY vil_backups/default.vil /tmp/default.vil
RUN python3 /tmp/vil_defaults_gen.py --input /tmp/default.vil \
    --output keyboards/m57/keymaps/via/vil_defaults.h --check

# stm32 linker scripts that vial-qmk doesn't ship by default.
COPY source/ld/*.ld platforms/chibios/boards/common/ld/

RUN make m57:via

# ---- export stage ----
# scratch image with just the artifact, so `--output type=local` extracts cleanly.
FROM scratch AS export
COPY --from=builder /vial-qmk/.build/m57_via.uf2 /
