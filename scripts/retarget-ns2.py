#!/usr/bin/env python3
"""FlashNX2: retarget update checks + app-own paths to the fork.

- Update checks point at Lucaspec72/FlashNX2 (upstream: Jonathan8520/FlashNX).
- The app's own SD dir becomes sdmc:/switch/FlashNX2/ so the fork never shares
  state (update markers, tiles, kill switches, cacert copy, trash) with an
  installed original FlashNX.
- Data dirs (sdmc:/flashnx, sdmc:/ruffle) are LEFT ALONE: same library layout,
  games/saves/profiles stay compatible with upstream.
- Jonathan8520's attribution is kept everywhere it is required (MIT).

Run from the repo root. Prints replacement counts; asserts every expected
replacement actually happened.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (subdir, filename-glob, old, new)
REPLACES = [
    # App's own SD dir (trailing-slash and bare-string forms)
    ("rust/src", ".rs", "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("cpp/src", None, "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("cpp/include", None, "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("third_party/ruffle/core/src", ".rs", "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("scripts", ".py", "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("rust/src", ".rs", '"sdmc:/switch/FlashNX"', '"sdmc:/switch/FlashNX2"'),
    ("cpp/src", None, '"sdmc:/switch/FlashNX"', '"sdmc:/switch/FlashNX2"'),
    ("cpp/src", None, "/switch/FlashNX/", "/switch/FlashNX2/"),
    # The .nro file name (comments + SELF_NRO default)
    ("rust/src", ".rs", "FlashNX.nro", "FlashNX2.nro"),
    ("cpp/src", None, "FlashNX.nro", "FlashNX2.nro"),
    ("forwarder/source", ".c", "sdmc:/switch/FlashNX/", "sdmc:/switch/FlashNX2/"),
    ("forwarder/source", ".c", "FlashNX.nro", "FlashNX2.nro"),
    # Trace log name
    ("cpp/src", None, "flashnx-trace.log", "flashnx2-trace.log"),
    # Sphaira association file (don't clobber the original's)
    ("cpp/src", None, "assoc/FlashNX.ini", "assoc/FlashNX2.ini"),
    # Update source
    ("rust/src", ".rs",
     "https://api.github.com/repos/Jonathan8520/FlashNX/releases/latest",
     "https://api.github.com/repos/Lucaspec72/FlashNX2/releases/latest"),
    # Homebrew-menu author (NACP; expanded into unquoted -D defines, so no
    # spaces/parens). Original-dev attribution elsewhere is untouched.
    ("cpp", "Makefile", "APP_AUTHOR  := Lucas\n", "APP_AUTHOR  := Lucaspec72\n"),
    # About by-line (keeps Jonathan8520; drops the "(AI)" tag)
    ("rust/src/library", ".rs",
     "FlashNX2 port by Lucaspec72 (AI)", "FlashNX2 port by Lucaspec72"),
]

changed = {}
for sub, ext, old, new in REPLACES:
    d = os.path.join(ROOT, sub)
    for dirpath, _dirs, files in os.walk(d):
        # Skip build artifacts and the cargo cache if a search root ever
        # covers them.
        parts = set(os.path.relpath(dirpath, d).replace("\\", "/").split("/"))
        if parts & {"target", "build", ".cargo-home"}:
            continue
        for fn in sorted(files):
            if ext and not fn.endswith(ext):
                continue
            # Never rewrite this script itself: its own `old` literals must
            # survive a run for the next run to be able to retarget again.
            if os.path.abspath(os.path.join(dirpath, fn)) == os.path.abspath(__file__):
                continue
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8") as f:
                s = f.read()
            n = s.count(old)
            if n:
                s2 = s.replace(old, new)
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(s2)
                rel = os.path.relpath(p, ROOT).replace("\\", "/")
                changed[(rel, old)] = changed.get((rel, old), 0) + n

for (rel, old), n in sorted(changed.items()):
    print(f"{n:3}x  {rel}: {old!r}")

# Assertions: the retargets that MUST exist afterwards.
must = [
    ("rust/src/updater.rs", "https://api.github.com/repos/Lucaspec72/FlashNX2/releases/latest"),
    ("rust/src/updater.rs", '"FlashNX2.nro"'),
    ("rust/src/updater.rs", "sdmc:/switch/FlashNX2/update_seen.txt"),
    ("rust/src/library.rs", "sdmc:/switch/FlashNX2/FlashNX2.nro"),
    ("cpp/src/main.cpp", "sdmc:/switch/FlashNX2/FlashNX2.nro"),
    ("cpp/src/main.cpp", '"/switch/FlashNX2/FlashNX2.nro"'),
    ("forwarder/source/main.c", "sdmc:/switch/FlashNX2/FlashNX2.nro"),
    ("cpp/src/updater.cpp", "sdmc:/switch/FlashNX2/cacert.pem"),
]
for rel, needle in must:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        if needle not in f.read():
            sys.exit(f"MISSING after retarget: {rel}: {needle}")

# And the old update URL must be gone.
with open(os.path.join(ROOT, "rust/src/updater.rs"), encoding="utf-8") as f:
    if "Jonathan8520/FlashNX/releases" in f.read():
        sys.exit("updater.rs still points at the original repo")

print("retarget OK")
