# FlashNX2

<p align="center">
  <strong>FlashNX2 — an unofficial Nintendo Switch 2 port of FlashNX.</strong><br>
  A fork of <a href="https://github.com/Jonathan8520/FlashNX">FlashNX</a> by Jonathan8520
  that targets the Switch 2 (libounce / OunceVK toolchain) so the same Flash games run on the newer console.<br>
  Powered by <a href="https://github.com/ruffle-rs/ruffle">Ruffle</a>, as upstream.
</p>

> **⚠️ Disclaimer — AI-generated port**
> This fork was created **entirely by AI** (OpenCode running GLM-5.3): the porting
> work, build tooling and documentation below the divider are all machine-generated.
> It is **unofficial** — not affiliated with, endorsed by, or (yet) reviewed by the
> original author. It has **not been fully validated on real hardware** yet (it
> builds; on-console testing is in progress — see [`PORT_NOTES.md`](PORT_NOTES.md)).
> Use at your own risk. For the supported Switch 1 experience, use the
> [original FlashNX](https://github.com/Jonathan8520/FlashNX).

## What's modified vs upstream

The port is deliberately **mechanical**: the engine, UI and gameplay code are
untouched upstream FlashNX; only what the Switch 2 toolchain requires changes.
One commit on top of upstream `97085c6` contains everything:

| Area | Files | What changed |
|:--|:--|:--|
| C++ build | `cpp/Makefile`, `forwarder/Makefile` | `switch2_rules` instead of `switch_rules`; `ARCH := $(SWITCH2_CPU)` (cortex-a78c); libounce `switch.specs`; app identity → FlashNX2 / 2.1.0-ns2.0 (identity strings must be paren- and space-free — expanded into unquoted `-D` defines) |
| C++ sources | `cpp/src/flashnx_heap.c` | bail out of newlib heap init when `fake_heap_*` don't describe a usable heap (libounce's mimalloc owns it) |
| C++ sources | `cpp/src/nsp.cpp` | libounce API divergence: `NacpStruct.lang[16]` → `NacpStruct.lang_data.lang[16]` (tracks HOS 21.x, where libnx froze) |
| Identity / updates | `rust/src/updater.rs`, `rust/src/bugreport.rs`, `rust/src/translate.rs`, `rust/src/library.rs`, `rust/src/lib.rs`, `rust/src/backend/render.rs`, `rust/src/library/settings_tab.rs`, `cpp/src/*`, `forwarder/source/main.c`, `scripts/make_standalone.py` | update checks target **`Lucaspec72/FlashNX2`** (never the original's releases); the app's own SD dir is `sdmc:/switch/FlashNX2/` so an installed original FlashNX shares nothing (update markers, HOME-menu tiles, kill switches, cacert copy, trash); game data dirs (`sdmc:/flashnx`, `sdmc:/ruffle`) are untouched — libraries/saves/profiles stay compatible with upstream, and the shared control-profile API still reads the original repo's community data on purpose; bug-report and translate relays point at the built-in `"example"` placeholder (no FlashNX2 worker exists; both fail gracefully instead of using the original's worker — deploy your own and fill the URLs to enable); version line bumped to **2.2.0** (releases must be tagged `v2.2.0`, `v2.2.1`, … — the update check parses numeric triples only); About screen + footer credit Jonathan8520 (MIT attribution, kept) and name the fork |
| Rust config | `rust/.cargo/config.toml`, `rust/rust-toolchain.toml` | target CPU `cortex-a78c`; host-agnostic `nightly` channel; Switch 2 linker flags |
| Rust lockfile | `rust/Cargo.lock` (force-added) | pins `libc 0.2.189` — libc 0.2.190+ (Oct 2026) dropped horizon coverage from `unix/newlib/mod.rs` and fails to compile for this target |
| Ruffle submodule | `third_party/ruffle` + `patches/ruffle-local-nobin.diff` | submodule pinned at the patched state; `patches/ruffle-local.diff` (upstream's local patches) regenerated without 8 payload-less binary test fixtures so it applies cleanly in the build container |
| Build tooling | `flashnx2.ps1`, `docker/` (Dockerfile, `rust-src-patches.py`), `scripts/build-ns2.sh`, `scripts/fix-libc-cache.py`, `scripts/patch-rust-src.sh` | Linux/Docker build path replacing upstream's Windows (MSYS2 + scoop) one; `ns2-rust-builder` image = devkita64 + headless JRE (for ruffle's `asc.jar`) + Rust nightly with two std patches (horizon `build.rs` restriction, deterministic `RandomState` seed); `fix-libc-cache.py` patches the extracted libc 0.2.190+ in the cargo registry cache because `cargo -Z build-std` resolves std's deps freshly and ignores both lock files |
| Docs | `PORT_NOTES.md` | full port record: every change, gotcha and open risk |

**Not included in the repo**: the Switch 2 devkit drop (`ounce-devkit-*`, with
libounce, the `switch2` portlibs and `switch2vars.sh`) — mount/read-only, never
modified. And `.cargo-home/` (git-ignored cargo cache).

> **Publishing note**: the `third_party/ruffle` submodule pin points at a local
> patched commit. Before publishing this repo, push that state to a Ruffle fork
> (e.g. `<you>/ruffle` branch `flashnx2`) and update `.gitmodules` so others can
> fetch it.

## Build (Switch 2)

Requirements: **Docker Desktop** running, plus the Switch 2 devkit drop
(`ounce-devkit-<date>` — found in this folder or any parent; or set
`$env:SWITCH2_DEVKIT` to its path).

```powershell
.\flashnx2.ps1 image        # (re)build the ns2-rust-builder image (one-time, auto on first build)
.\flashnx2.ps1 build        # build cpp/FlashNX2.nro (~32 MB)
.\flashnx2.ps1 build -Dev   # release-dev profile, thin LTO, faster iteration
.\flashnx2.ps1 clean
.\flashnx2.ps1 shell        # interactive bash in the container
```

Output: **`cpp/FlashNX2.nro`** — copy to `sdmc:/switch/` and launch from the
homebrew menu (Switch 2 with homebrew/HEN loader). The forwarder NSP it embeds
(`forwarder/forwarder.nsp`) is for a future HOME Menu tile and is not yet
validated.

Status: **builds clean end-to-end** (Rust staticlib → forwarder → C++ link
against libounce → nro). On-console testing is the remaining milestone — open
risks (audio `audren` vs `audu`, GL 4.3 via Zink, EGL stencil, heap
accounting) are tracked in [`PORT_NOTES.md`](PORT_NOTES.md).

---

# Original FlashNX readme

<p align="center">
  <img src="assets/banner.png" alt="FlashNX" width="480">
</p>

<p align="center">
  <strong>Play Flash games on your Nintendo Switch.</strong><br>
  FlashNX runs <code>.swf</code> games (ActionScript 1, 2 and much of 3) and downloads them for you from the Flashpoint Archive.<br>
  Powered by <a href="https://github.com/ruffle-rs/ruffle">Ruffle</a>.
</p>

<p align="center">
  <a href="https://hb-app.store/switch/FlashNX"><img src="https://img.shields.io/badge/Homebrew%20App%20Store-FlashNX-2ea44f" alt="Homebrew App Store"></a>
  <a href="https://github.com/Jonathan8520/FlashNX/releases"><img src="https://img.shields.io/github/v/release/Jonathan8520/FlashNX?label=release" alt="Release"></a>
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fflashnx.j-levy228.workers.dev%2Fdownloads" alt="Downloads">
  <img src="https://img.shields.io/badge/platform-Nintendo%20Switch-e60012" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
</p>

<p align="center">
  <img src="assets/screenshots/play.png" alt="The Play tab: your library" width="100%">
</p>

| Getting games | In game |
|:---:|:---:|
| ![The Import tab: Flashpoint shelves and your sources](assets/screenshots/import.png) | ![The pause menu over a game](assets/screenshots/pause.png) |

## Install

1. You need a Switch running **Atmosphère**.
2. Install **FlashNX** from the **[Homebrew App Store](https://hb-app.store/switch/FlashNX)**, or copy **`FlashNX.nro`** from the [latest release](https://github.com/Jonathan8520/FlashNX/releases/latest) to **`sdmc:/switch/FlashNX/`**.
3. Open FlashNX **once from the Album** and choose **Install**: it puts its icon on the HOME Menu. From then on, start it from that icon, which gives it the console's full memory. This needs signature patches (sys-patch), like any homebrew icon on the HOME Menu.

Without signature patches, **hold R while opening any game from the HOME Menu**, then pick FlashNX in the Homebrew Menu: it gets the full memory too.

## Get games

- **From the console**: the **Import** tab shows games from the [Flashpoint Archive](https://flashpointarchive.org/), a random studio and random games, without adult, crude or gory ones. **A** downloads a game with its cover and the files it needs, **+** shows its details first, **X** searches by name.
- **From a web address**: a direct `.swf` link, an archive.org item or a Wayback Machine snapshot, in the same tab.
- **From a computer**: copy `.swf` files to **`sdmc:/flashnx/`**. A `<game>.png` or `.jpg` next to one becomes its cover.

## Play

**In the library**, the bottom of the screen shows what the buttons do. Also: **L / R** change tab, **ZL / ZR** change folder, **X** changes the layout (grid, list, strip or shelf).

**In a game**, **−** opens the pause menu. Every game starts with a ready-made layout: the left stick for the arrow keys, A for Space, the right stick or touch for the mouse cursor, ZR to click. The pause menu changes any of it, for that game only:

- **Controls and cursor**: any button to any key or mouse click. Holding ZL, ZR, L or R gives the buttons a second key.
- **Up to four players**, each with their own controller and keys. A single Joy-Con held sideways counts as a whole controller.
- **Shared profiles**: download the controls other players made for a game, or share yours.
- **Screen** (display, rotation, zoom, filters), **Overclock**, **Restart** and **Quit**.

## Features

- A **HOME Menu icon** for any game, with its name and cover, that starts straight into it.
- **Folders**: a game can be in several, and its file stays where it is.
- **Saves** kept on the SD card, and **play time** for each game.
- **1080p on a TV**: docked, games are drawn at the TV's resolution.
- **Overclock AUTO** raises the CPU only while a game falls behind, and only if it helps.
- **Gyroscope cursor**: aim like a Wii remote, or tilt the console like a tray with a marble on it.
- **9 languages**, picked from the console's language.
- **Report a bug or send a suggestion** from Settings, with no account.

## Turn a game into its own Switch app

<p align="center">
  <img src="assets/screenshots/make-standalone.png" alt="make_standalone.py, the window" width="720">
</p>

**`make_standalone.py`** puts FlashNX and one game into a single `.nro`: an app with its own name and picture in the Homebrew Menu, which starts straight into the game. Nothing else to install on the Switch.

1. Install [Python](https://www.python.org/downloads/) on your computer.
2. Download **`make_standalone.py`** from the [latest release](https://github.com/Jonathan8520/FlashNX/releases/latest) and double-click it.
3. Drop the game's `.swf` on the window: the files FlashNX downloaded with it come along. Check the name and the picture, then press **Make the .nro**.
4. Copy the app to `sdmc:/switch/<Its_Name>/` on the SD card.

**Update an app...** moves an app made earlier to a newer FlashNX, keeping its game. Command line and details: [DEVELOPMENT.md](DEVELOPMENT.md#without-building-anything-scriptsmake_standalonepy).

## Known limitations

- **Not every game works**: compatibility, especially for ActionScript 3, is [Ruffle's](https://ruffle.rs/compatibility). Report a game that does not work from **Settings › Help and feedback › Report a bug**.
- **Heavy games can slow down.** Overclock AUTO helps where it can.
- **No savestates.** The games' own saves work.
- **Audio** can crackle a little in very busy scenes.

## Credits & licenses

FlashNX is only a **Switch integration layer**. All credit for the Flash emulation goes to **Ruffle**.

- **[Ruffle](https://github.com/ruffle-rs/ruffle)** *(Apache-2.0 / MIT)*: the Flash engine, SWF parsing and the ActionScript virtual machines. FlashNX embeds `ruffle_core`, `ruffle_render`, `ruffle_video_software`, `naga-agal` and `swf`.
- **[devkitPro](https://devkitpro.org/) / libnx** *(ISC)*: Switch toolchain and Horizon API.
- **[switch-mesa](https://github.com/devkitPro/pacman-packages)** *(MIT)*: OpenGL/GLES via Nouveau, the graphics backend, with a modified copy of devkitPro's **libdrm_nouveau** *(MIT)* built in (`cpp/third_party/libdrm_nouveau`).
- **[Game_Music_Emu](https://github.com/libgme/game-music-emu)** *(LGPL-2.1 or later, with emu2413 under MIT)*: the sound chip emulators some games play their music with, built in (`cpp/third_party/gme`).
- **Networking**: [libcurl](https://curl.se/) · [Mbed TLS](https://github.com/Mbed-TLS/mbedtls) · [zlib](https://zlib.net/) · [Mozilla](https://curl.se/docs/caextract.html) CA bundle.
- **Rust crates**: [jpeg-decoder](https://github.com/image-rs/jpeg-decoder) (a fork patched for newlib, `third_party/jpeg-decoder-switchfork`) · `jpeg-encoder` · `png` · `image-webp` · `ttf-parser` · `ab_glyph_rasterizer` · `serde` · `serde_json` · `flate2` · `dlmalloc` · `url` · `encoding_rs` · `naga` · `whichlang`, plus Ruffle's own dependencies.
- **[Lucide](https://lucide.dev/)** *(ISC, with icons from Feather under MIT)*: the interface icons, as a font subset built by `scripts/make_icon_font.py`; both notices are in `rust/src/backend/render/kit/icons-LICENSE.txt`.
- **[Flashpoint Archive](https://flashpointarchive.org/)**: the Flash preservation project. FlashNX uses its public APIs so you can find cover art and download the games you choose. Preserved games remain the property of their original creators, and FlashNX only fetches what you explicitly request. The Flashpoint logo in the Import tab is the Flashpoint Archive's, under [CC BY 4.0](https://flashpointarchive.org/branding) (`assets/flashpoint.png`: its colorized version, cropped and resized).
- **[Internet Archive](https://archive.org/)**: the archive.org items and Wayback Machine snapshots the Import tab can take a game from.

**License**: the FlashNX integration code is under the **MIT** license (see [`LICENSE`](LICENSE)). Ruffle and the other dependencies keep their own.

---

**Architecture, build and technical notes**: [DEVELOPMENT.md](DEVELOPMENT.md) · **Changelog**: [CHANGELOG.md](CHANGELOG.md)
