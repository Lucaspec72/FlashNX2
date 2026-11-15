#!/usr/bin/env python3
# FlashNX2 (Switch 2 port): apply FlashNX's two rust-src patches to a freshly
# installed Linux nightly toolchain, inside the build image. Same two patches
# the repo's scripts/patch-rust-src.sh applies on Windows; kept separate so the
# image can bake them in (they are erased by every toolchain update, so the
# image is the reliable place for them).
#
# Usage: python3 rust-src-patches.py <std-dir>   (…/lib/rustlib/src/rust/library/std)
import sys

std = sys.argv[1]
build_rs = std + "/build.rs"
random_rs = std + "/src/hash/random.rs"

# --- Patch 1: allow std for the Switch (Horizon) target -> no restricted_std ---
s = open(build_rs, encoding="utf-8").read()
if 'target_os == "horizon"' in s:
    print("Patch 1 (build.rs): already applied")
else:
    anchor = '        || (target_vendor == "nintendo" && target_env == "newlib")\n'
    if anchor not in s:
        sys.exit("Patch 1: anchor line not found in build.rs (upstream layout changed?)")
    s = s.replace(
        anchor,
        anchor + '        || (target_vendor == "nintendo" && target_os == "horizon")\n',
        1,
    )
    open(build_rs, "w", encoding="utf-8").write(s)
    print("Patch 1 (build.rs): APPLIED")

# --- Patch 2: deterministic RandomState on Horizon (thread_local crashes) ------
s = open(random_rs, encoding="utf-8").read()
if 'target_os = "horizon"' in s:
    print("Patch 2 (random.rs): already applied")
else:
    anchor = "    pub fn new() -> RandomState {\n"
    if anchor not in s:
        sys.exit("Patch 2: anchor 'pub fn new() -> RandomState {' not found")
    inject = (
        "    // FlashNX-horizon-randomstate: the thread_local RNG below crashes on\n"
        "    // Switch (Horizon); use a deterministic process-static counter there.\n"
        "    #[allow(unreachable_code)]\n"
        "    pub fn new() -> RandomState {\n"
        "        #[cfg(target_os = \"horizon\")]\n"
        "        {\n"
        "            use crate::sync::atomic::{AtomicU64, Ordering};\n"
        "            static K0: AtomicU64 = AtomicU64::new(0x9E3779B97F4A7C15);\n"
        "            let k0 = K0.fetch_add(1, Ordering::Relaxed);\n"
        "            return RandomState { k0, k1: 0x517CC1B727220A95 };\n"
        "        }\n"
    )
    open(random_rs, "w", encoding="utf-8").write(s.replace(anchor, inject, 1))
    print("Patch 2 (random.rs): APPLIED")

# NOTE: an earlier "Patch 3" here rewrote the rust-src library/Cargo.lock to
# pin libc 0.2.189. It is GONE because it cannot work: cargo's -Z build-std
# resolves std's dependencies freshly against crates.io and consults neither
# library/Cargo.lock nor the app's Cargo.lock (verified empirically — the lock
# was byte-identical after a build). The working fix is
# scripts/fix-libc-cache.py in the repo, which patches the EXTRACTED libc
# crate in the cargo registry cache before every build (run from
# scripts/build-ns2.sh). See FlashNX2/PORT_NOTES.md for the full story.


