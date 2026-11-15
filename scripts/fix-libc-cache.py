#!/usr/bin/env python3
"""Restore the `horizon` branch libc 0.2.190+ removed from unix/newlib/mod.rs.

Why this exists (FlashNX2): `cargo -Z build-std` resolves std's dependencies
FRESHLY against crates.io — it consults neither the rust-src
`library/Cargo.lock` (verified: unchanged after a build) nor the app's
Cargo.lock. So std always pulls the newest libc into the shared registry
cache, and libc 0.2.190/0.2.191 broke aarch64+horizon: the dev_t cfg_if in
`unix/newlib/mod.rs` used to let horizon fall into a plain `else`
(dev_t=u32, ino_t=u32, off_t=i64) but now ends in
`compile_error!("unsupported target")` after an arm/powerpc-only branch was
inserted. The module selection itself is fine — target_os="horizon" still
selects a dedicated `mod horizon` before the arch fallback is reached.

Since lock pinning cannot influence build-std's resolution, we patch the
EXTRACTED crate inside the cargo registry cache (CARGO_HOME, which persists
in the workspace) — exactly the source path rustc compiles. Idempotent.
Run before every cargo build (see scripts/build-ns2.sh).
"""
import glob
import os
import re
import sys

cargo_home = os.environ.get("CARGO_HOME", "")
if not cargo_home:
    sys.exit("fix-libc-cache: CARGO_HOME is not set")

paths = sorted(glob.glob(f"{cargo_home}/registry/src/*/libc-0.2.*/src/unix/newlib/mod.rs"))
if not paths:
    print("fix-libc-cache: no extracted libc found yet (nothing to do)")
    sys.exit(0)

# The 0.2.190+ dev_t cfg_if inserts this arm/powerpc branch before the
# compile_error else. We add a horizon branch ahead of it with the exact
# types <=0.2.189's plain `else` gave every remaining target (incl. horizon).
ANCHOR = '} else if #[cfg(any(target_arch = "arm", target_arch = "powerpc"))] {'
BRANCH = (
    '} else if #[cfg(target_os = "horizon")] {\n'
    '        pub type dev_t = u32;\n'
    '        pub type ino_t = u32;\n'
    '        pub type off_t = i64;\n'
    '    '
)

for path in paths:
    crate = path.split("/registry/src/")[-1].split("/src/")[0]
    s = open(path, encoding="utf-8").read()
    if "pub type dev_t = c_short;" not in s:
        print(f"fix-libc-cache: {crate}: unexpected newlib layout, skipped")
        continue
    dev_idx = s.index("pub type dev_t = c_short;")
    anchor_idx = s.find(ANCHOR, dev_idx)
    if anchor_idx == -1:
        # Pre-0.2.190 layout: horizon is covered by the plain `else`. Only
        # warn if that block still ends in a compile_error.
        block = s[dev_idx:s.find("\ncfg_if!", dev_idx)]
        if "compile_error!" in block and 'target_os = "horizon"' not in block:
            print(f"fix-libc-cache: WARNING {crate}: unrecognized dev_t cfg_if "
                  "without horizon coverage - build may fail")
        else:
            print(f"fix-libc-cache: {crate}: horizon already covered, nothing to do")
        continue
    segment = s[dev_idx:anchor_idx]
    if 'target_os = "horizon"' in segment:
        print(f"fix-libc-cache: {crate}: already patched")
        continue
    s2 = s[:anchor_idx] + BRANCH + s[anchor_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(s2)
        f.flush()
        os.fsync(f.fileno())
    # Assert the write stuck (learned from the Patch 3 silent-no-op incident).
    check = open(path, encoding="utf-8").read()
    if 'target_os = "horizon"' not in check[check.index("pub type dev_t = c_short;"):]:
        sys.exit(f"fix-libc-cache: {crate}: write did not stick (readback mismatch)")
    print(f"fix-libc-cache: {crate}: PATCHED (horizon dev_t branch restored)")
