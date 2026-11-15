# FlashNX2 build image: the workspace's devkitPro devkita64 image plus a Rust
# nightly toolchain, for building FlashNX's Ruffle staticlib
# (target aarch64-nintendo-switch-freestanding, std-via-newlib, -Z build-std).
#
# Rebuild with:  .\FlashNX2\flashnx2.ps1 image     (or docker build manually)
# Why an image: dev.ps1 containers are --rm, so anything installed inside one
# run is lost. Baking the toolchain in keeps every FlashNX2 build one command.
#
# NOTE: this image replaces the base for FlashNX2 builds only; dev.ps1 keeps
# using devkitpro/devkita64 for the other projects. If a project needs Rust
# later, reuse this image (rename ns2-rust-builder -> ns2-builder then).
FROM devkitpro/devkita64:latest

# Java (headless JRE): ruffle_core's build script compiles the AVM2
# playerglobal definitions with Adobe's asc.jar via `java -jar` (see
# third_party/ruffle/core/build_playerglobal/src/avm2.rs). No javac needed.
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jre-headless \
 && rm -rf /var/lib/apt/lists/*

# Rust under /opt so every container from this image sees it, whatever the
# user's HOME is.
ENV RUSTUP_HOME=/opt/rustup
ENV CARGO_HOME=/opt/cargo
ENV PATH="/opt/cargo/bin:${PATH}"

RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain nightly --profile minimal \
 && rustup component add rust-src \
 && rm -rf "${RUSTUP_HOME}/downloads" "${CARGO_HOME}/registry/cache" "${CARGO_HOME}/git"

# FlashNX's two rust-src patches (see scripts/patch-rust-src.sh in the repo for
# the full rationale). Applied at image build time: a rustup update here means
# a docker build, not a silent loss.
COPY rust-src-patches.py /tmp/rust-src-patches.py
# The verification greps are deliberate: writes inside a RUN step MUST show up
# in the committed layer (a silent no-op cost us an afternoon once). Patches 1
# and 2 are asserted by markers; std's libc 0.2.190+ problem is handled at
# build time by scripts/fix-libc-cache.py (build-std ignores this lockfile).
RUN STD="$(rustc --print sysroot)/lib/rustlib/src/rust/library/std" \
 && python3 /tmp/rust-src-patches.py "$STD" \
 && grep -q 'target_os == "horizon"' "$STD/build.rs" \
 && grep -q 'target_os = "horizon"' "$STD/src/hash/random.rs" \
 && rm /tmp/rust-src-patches.py

# Smoke-check the toolchain actually answers.
RUN rustc --version && cargo --version
