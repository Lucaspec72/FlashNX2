#!/usr/bin/env bash
# FlashNX2 (Switch 2 port) build orchestrator — runs INSIDE the build container
# (image ns2-rust-builder, see ../docker/Dockerfile), from /work/FlashNX2/FlashNX.
#
# FlashNX upstream's scripts/build.sh targets Windows (cargo on the host, make
# in devkitPro's MSYS2 bash). On Switch 2 everything runs in the Linux
# container, so the orchestration is simpler: no MSYS2 hop, no scoop paths.
#
# Usage: bash scripts/build-ns2.sh [release|dev]
#   release : LTO=full (default, matches upstream ./scripts/build.sh)
#   dev     : release-dev profile, thin LTO, fast iteration
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PROFILE="release"
CARGO_FLAG="--release"
if [[ "${1:-}" == "dev" ]]; then
    PROFILE="release-dev"
    CARGO_FLAG="--profile release-dev --features instr"
fi

# switch2vars.sh (workspace-level devkit drop) sets DEVKITPRO/DEVKITA64 and the
# switch2 portlib paths. Same file dev.ps1 sources.
source /work/ounce-devkit-20261114/switch2vars.sh

# Persist the crates.io download cache in the workspace: the container is
# --rm, so CARGO_HOME=/opt/cargo (image default) would re-download every crate
# on every build. rustup stays in the image; only cargo's cache moves.
export CARGO_HOME=/work/FlashNX2/.cargo-home
mkdir -p "$CARGO_HOME"

# build-std resolves std's dependencies freshly against crates.io (it ignores
# BOTH the rust-src library/Cargo.lock and this workspace's Cargo.lock), so
# newer libc releases land in the shared registry cache even though our graph
# pins libc 0.2.189. libc 0.2.190+ breaks aarch64+horizon in
# unix/newlib/mod.rs; patch the extracted crate before building. Idempotent.
python3 "$ROOT/scripts/fix-libc-cache.py"

echo "[1/3] Building Rust staticlib (profile: $PROFILE)..."
(cd "$ROOT/rust" && cargo build $CARGO_FLAG)

# Relink-on-profile-change, same idea as upstream build.sh.
STAMP="$ROOT/cpp/build/.rust_profile"
if [[ "$(cat "$STAMP" 2>/dev/null)" != "$PROFILE" ]]; then
    rm -f "$ROOT/cpp/FlashNX2.elf"
    touch "$ROOT/cpp/src/prof.cpp" "$ROOT/cpp/src/main.cpp"
    mkdir -p "$ROOT/cpp/build"
    echo "$PROFILE" > "$STAMP"
fi

echo "[2/3] Building the tile forwarder (switch2_rules)..."
make -C "$ROOT/forwarder"
cp "$ROOT/forwarder/forwarder.nsp" "$ROOT/forwarder/flashnx_forwarder.nsp"
/opt/devkitpro/tools/bin/bin2s "$ROOT/forwarder/flashnx_forwarder.nsp" \
    > "$ROOT/cpp/src/flashnx_forwarder.s"

echo "[3/3] Building C++ wrapper and linking .nro (libounce)..."
make -C "$ROOT/cpp" RUST_PROFILE=$PROFILE

echo
echo "Done. Output: cpp/FlashNX2.nro"
ls -la "$ROOT/cpp/FlashNX2.nro" 2>/dev/null || echo "(.nro not found — build failed)"
