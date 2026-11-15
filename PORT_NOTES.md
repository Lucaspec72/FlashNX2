# FlashNX2 — PORT NOTES

**What:** FlashNX (homebrew Flash player for Switch, powered by Ruffle) forked
and ported to **Switch 2** (libounce + OunceVK GL stack).
**Upstream:** https://github.com/Jonathan8520/FlashNX (MIT) — this repo IS the
fork (a clone edited in place); upstream files keep the
`flash-for-switch` / `ruffle_switch` internal names, only identity bits
(`TARGET`, `APP_TITLE`, version) change to FlashNX2. The README's top section
has the repo-facing summary and the AI-generated-port disclaimer.

## Layout

**2026-11-15 update: the repo is now SELF-CONTAINED** — `flashnx2.ps1` (at the
repo root), `docker/`, this PORT_NOTES.md and `.cargo-home/` (git-ignored) all
moved INTO the clone, and `build-ns2.sh` no longer hardcodes the workspace
layout: `flashnx2.ps1` finds the devkit drop (this folder or any parent, or
`$env:SWITCH2_DEVKIT`), mounts it read-only at `/devkit`, and passes
`SWITCH2_DEVKIT=/devkit` to the container; `CARGO_HOME=$ROOT/.cargo-home`.
So a fresh `git clone` + the devkit drop + Docker is all a build needs.
The README's top section is the repo-facing summary + AI disclaimer.

- `flashnx2.ps1` — build wrapper (repo root; manages the build image)
- `docker/Dockerfile` + `docker/rust-src-patches.py` — build image
  `ns2-rust-builder`: devkitpro/devkita64 + headless JRE (ruffle's asc.jar)
  + Rust nightly + rust-src patches baked in (containers are `--rm`, so
  toolchains must live in an image, not in a container)
- Build: `.\flashnx2.ps1 build` → `cpp/FlashNX2.nro`
  (add `-Dev` for the fast release-dev profile)
- Container-side orchestrator: `scripts/build-ns2.sh` (replaces the
  Windows-only `scripts/build.sh`; no MSYS2 hop, everything in Linux bash;
  also auto-pins libc 0.2.189 in the app graph on fresh clones)

## Identity / network retarget (2026-11-15, `scripts/retarget-ns2.py`)

The fork never talks to the original repo for updates, and shares no SD state
with an installed original FlashNX:

- **Update check** (`rust/src/updater.rs`): latest-release API →
  `https://api.github.com/repos/Lucaspec72/FlashNX2/releases/latest`, asset
  name `FlashNX2.nro`. `scripts/make_standalone.py`'s downloader retargeted
  the same way.
- **App's own SD dir**: `sdmc:/switch/FlashNX/` → `sdmc:/switch/FlashNX2/`
  everywhere (rust + cpp + the tile forwarder's DEFAULT_NRO/NRO_NOTE/
  TILE_CFG_FMT): update markers, HOME-menu tiles, `noalloc.on`/`dlmalloc.off`
  kill switches, `cacert.pem` copy, trash dir, prof/heapprof outputs, trace
  log (`flashnx2-trace.log`), Sphaira association (`assoc/FlashNX2.ini`).
  An installed original FlashNX shares NOTHING with it.
- **Game data dirs stay upstream**: `sdmc:/flashnx/` and `sdmc:/ruffle/`
  (games, saves, favorites, tags, playtime, control profiles) — a FlashNX2
  install reads the same library as FlashNX would.
- **Shared control profiles** (`rust/src/profiles.rs` `GH_API_BASE`):
  DELIBERATELY still `api.github.com/repos/Jonathan8520/FlashNX/contents/` —
  that is community data (game control mappings), not app updates; pointing
  the fork at its own repo would orphan it from every existing profile.
- **Bug report + translate relays** (`rust/src/bugreport.rs`,
  `rust/src/translate.rs`): upstream's Cloudflare Worker deployment
  (`flashnx.j-levy228.workers.dev`) is NOT used — reports must not file
  issues on the original repo. Both endpoints now use the built-in
  `"example"` placeholder, which makes them fail gracefully ("endpoint not
  configured" / feature-off toast). Deploy `tools/bug-report-worker/` for
  FlashNX2 and fill both URLs to enable.
- **Version**: `bugreport::APP_VERSION` = "2.2.0" and nacp `APP_VERSION`
  2.2.0. FlashNX2 releases must be tagged `v2.2.0`, `v2.2.1`, ... —
  `parse_version` keeps only the numeric triple (a `2.1.0-x` suffix parses
  as 2.1.0 and would never read as newer than the running build).
- **Attribution kept**: About by-line "Jonathan8520 · FlashNX2 port by
  Lucaspec72 (AI)", footer band "Jonathan8520 · FlashNX2 · v2.2.0", About
  source row → github.com/Lucaspec72/FlashNX2, bug link → .../FlashNX2/issues.

## Build status log

- **FlashNX2.nro: BUILDS.** `cpp/FlashNX2.nro` (~32 MB) — full pipeline
  green: Rust staticlib (Ruffle + std, ~4 min warm) → forwarder .nsp → C++
  wrapper + link against libounce → nacp → nro (2026-11-15).
  First on-console test is the next milestone; see the open-risks checklist
  below.
- **Rust staticlib: BUILDS.** `libruffle_switch.a` compiles for
  `aarch64-nintendo-switch-freestanding` (std via build-std, ~4 min warm).
  Blocked earlier by: fresh submodule (needs ruffle-local-nobin.diff), libc
  0.2.190+ horizon regression (see below), and Java for asc.jar (now in the
  image).
- **Forwarder: BUILDS** under switch2_rules → `forwarder/forwarder.nsp`.
  libounce's npdmtool prints several "Failed to get X (field not present)"
  lines for it — fields unset in its .json defaults; appears benign, verify
  the .nsp installs a working tile on console.
- cpp/Makefile gotcha: APP_TITLE/APP_AUTHOR/APP_VERSION are expanded into
  unquoted `-D` compile defines — **no parentheses AND no spaces** in them
  (parens = `/bin/sh: Syntax error: "(" unexpected`; spaces = the compiler
  sees the extra words as input files → "cannot specify '-o' ... with
  multiple files"). The defines themselves keep a single-word fallback:
  `Lucas`.
- libounce API divergence #1: `NacpStruct` no longer has `lang[16]` — the
  entries moved into `NacpStruct.lang_data` (`NacpLanguageEntryData`, a
  union of `lang[16]` and compressed-data). `cpp/src/nsp.cpp` patched
  (`nacp.lang[l]` → `nacp.lang_data.lang[l]`). Expect more of these: libounce
  tracks the newer HOS API (21.x) where libnx froze at older semantics.

## Ruffle submodule patching (REQUIRED before any build)

`third_party/ruffle` is checked out at upstream `ruffle-rs/ruffle` @
`71280cd1`; ALL of FlashNX's engine work (flashnx_jit baseline JIT, instr
features, SM63/SSF2 fixes, Matryoshka unpacking, libgme hooks, ...) lives in
`patches/ruffle-local.diff` (the numbered `0001-0003` patches are subsets kept
for upstream-PR reference). A fresh submodule build fails immediately with
`ruffle_core does not have that feature: flashnx_instr`.

Application quirk: `ruffle-local.diff` carries 8 payload-less binary test
fixtures (`tests/tests/swfs/**/test.swf`), which make plain `git apply` die
with "git diff header lacks filename information" even with `--exclude`.
`patches/ruffle-local-nobin.diff` (generated here, same diff minus those 8
blocks — they are test-suite fixtures only, never needed for the player
build) applies cleanly:

    git -C third_party/ruffle apply ../../patches/ruffle-local-nobin.diff

## Dependency hazard: libc 0.2.190+ vs aarch64+horizon (TWO different fixes)

`libc` 0.2.190/0.2.191 removed horizon's coverage from the dev_t `cfg_if` in
`unix/newlib/mod.rs`: ≤0.2.189 let every remaining target (incl. horizon)
fall into a plain `else` (`dev_t=u32, ino_t=u32, off_t=i64`); 0.2.190+ added
an `arm/powerpc` branch and turned the `else` into
`compile_error!("unsupported target")` — fatal for aarch64+horizon with
FlashNX's injected `--cfg target_env="newlib"`. (The module selection itself
is fine: `target_os = "horizon"` still selects a dedicated `mod horizon`
before the arch fallback. The remaining time_t delta — `c_longlong` → `i64`
— is the same 64-bit type on aarch64, so the dev_t branch is the only fix
needed.)

**Fix 1 — our dependency graph** (`rust/Cargo.lock`, force-added to git in
this fork — upstream git-ignores it): a fresh clone resolves libc to the
newest 0.2.x → `cargo update libc --precise 0.2.189`. Done, and the pin is
committed; `build-ns2.sh` also re-pins automatically if the lock is missing
or wrong. This pin IS honored for the app graph.

**Fix 2 — std's copy (the hard one):** `-Z build-std` resolves std's
dependencies FRESHLY against crates.io and consults **neither** the rust-src
`library/Cargo.lock` (verified byte-identical after a build) **nor** the
app's Cargo.lock, and the `library/.cargo/config.toml` vendored-sources
replacement never comes into play either. Lock pinning therefore cannot
influence it at all (an image-side "Patch 3" that rewrote the library lock
was built, verified... and useless — removed again). The working fix:
`scripts/fix-libc-cache.py`, run by `build-ns2.sh` before every
build — it inserts a horizon branch (`dev_t=u32, ino_t=u32, off_t=i64`,
exactly what ≤0.2.189 gave) into the EXTRACTED libc-0.2.190+ crate inside
`.cargo-home/registry/src/` (CARGO_HOME persists inside the repo),
which is exactly the source path rustc compiles. Idempotent, readback-asserted.
If `.cargo-home` is ever wiped, the first build re-downloads the broken libc
and fails; the second run of `build-ns2.sh` patches it and succeeds (cold
cache also slows the first build). Never delete `.cargo-home` casually.

Fallback option if this ever becomes unmaintainable: pin the build image's
nightly to a date before libc 0.2.190's release (2026-10-02), e.g.
`nightly-2026-09-30`, whose rust-src lock predates the break — but that
trades a known-good current rustc for an older one, so it is plan B.

If OTHER crates.io deps break the same way (fresh lock = newest of
everything), pin them the same way in the app graph.

## What was changed vs upstream (source level)

1. `cpp/Makefile` — `switch2_rules` instead of `libnx/switch_rules`;
   `ARCH := $(SWITCH2_CPU) -mtp=soft -fPIE` (cortex-a78c from
   `libounce/switch2_cpu.mk`); `-specs=$(DEVKITPRO)/libounce/switch.specs`;
   `TARGET/APP_TITLE/APP_VERSION` → FlashNX2. LIBS unchanged: `-lEGL` now
   resolves to the switch2 stub (OunceVK GL / Zink), `-lglapi -lGLESv2` to the
   switch2 portlibs' EMPTY shadow archives, `-lcurl -lmbedtls* -lz` still come
   from the Switch 1 portlibs via `$(PORTLIBS)`, `-lnx` gets libounce.
2. `forwarder/Makefile` — same three changes (used for the HOME-menu tiles).
3. `rust/.cargo/config.toml` — `target-cpu=cortex-a78c` (was cortex-a57).
   Everything else (target `aarch64-nintendo-switch-freestanding`, newlib-env
   cfg injections, getrandom=custom) untouched — libounce is libnx-compatible
   at source level and the Rust side never calls libnx directly (all libnx
   usage is in the C++ side).
4. `rust/rust-toolchain.toml` — channel `nightly` (host-agnostic; the Rust
   build runs in the Linux container).
5. `scripts/patch-rust-src.sh` — toolchain name parameterized (`RUST_TC`,
   default `nightly`).
6. `cpp/src/flashnx_heap.c` — `init_locked` now bails out (stays inert) when
   `fake_heap_start/end` don't describe a usable heap. On Switch 2 the heap is
   mimalloc-managed (libounce), so newlib's sbrk extents may not describe it;
   the -Wl,--wrap hooks then simply never fire and every allocation goes to
   the console allocator (mimalloc is fragmentation-tolerant, which is what
   FlashNX's big-heap region was working around on Switch 1).
7. `third_party/libdrm_nouveau` is STILL COMPILED (kept in SOURCES): the Rust
   side references its buffer-object-cache stat symbols, and on Switch 2 its
   objects are dead weight (OunceVK's Mesa is self-contained — the switch2
   portlibs even ship an empty libdrm_nouveau.a shadow). Removing the dir from
   the build would break the link without further work.

## Open risks / on-console TODO (first FlashNX2.nro test)

- [ ] **audren** (cpp/src/audio.cpp): Switch 1 audio service. TOOLBOX open
  question: does audren work on Switch 2, or must ports use audu
  (switch2/services/audu.h)? If audren fails to open at boot, port the
  SwitchAudioBackend's calls to audu.
- [ ] **GL version**: `rust/src/ffi/gl.rs` is a hand-written GL 4.3 core
  subset. OunceVK GL is Zink over NVK — desktop GL should be available; if the
  context comes back at a lower version, add a fallback to the GLES 3.1 path.
- [ ] **EGL_STENCIL_SIZE=8** (cpp/src/gl_context.cpp): verify Zink honors it
  (FlashNX uses stencil for Flash masking).
- [ ] **appletSetCpuBoostMode / svcGetInfo RAM / jit**: should exist in
  libounce; unverified at runtime.
- [ ] **ncm/ns HOME-menu tiles** (cpp/src/nsp.cpp): installed tiles are a
  Switch 1 concept that should work identically; unverified.
- [ ] **A78C vs A57 codegen**: the Rust flags retune only the CPU model; if
  Ruffle's interpreter regresses (unlikely — A78C is strictly better OoO),
  measure with the --dev prof build.
- [ ] **Heap size**: FlashNX asks hbloader for full memory; Switch 2 heap
  accounting via switch2/memory/heap.h if anything reads mallinfo.

## Env / tooling notes (promote to TOOLBOX.txt when proven)

- `ns2-rust-builder` image = devkita64 + headless JRE (ruffle_core's build
  script runs Adobe's `asc.jar` via `java -jar` to compile the AVM2
  playerglobal — upstream needed Java on Windows too) + Rust nightly
  (rustup under /opt/rustup, cargo under /opt/cargo) + FlashNX rust-src
  patches applied at image build time. Other projects needing Rust can
  reuse it.
- Building Rust staticlibs for `aarch64-nintendo-switch-freestanding` needs
  `-Z build-std` (tier-3 target) → nightly + rust-src; the build is
  host-side, no target linker involved (staticlib), so the final link stays
  in the C++ Makefile.
- Switch 1 portlibs (curl/mbedtls/zlib) link fine against libounce (source
  compatible); runtime behavior still to be confirmed on console.
