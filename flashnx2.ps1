# FlashNX2 - build wrapper (run from anywhere; paths are relative to this
# file, which lives at the repo root).
#
# Builds the FlashNX2 .nro (FlashNX fork ported to Switch 2 / libounce) inside
# a dedicated Docker image that adds a Rust nightly toolchain on top of
# devkitpro/devkita64. The Ruffle staticlib needs cargo; the base image has
# none, and containers are --rm, so the toolchain lives in an image.
#
# Usage:
#   .\flashnx2.ps1 build   [-Dev]   build the .nro (release or release-dev)
#   .\flashnx2.ps1 clean            make clean + cargo clean
#   .\flashnx2.ps1 image            (re)build the ns2-rust-builder image
#   .\flashnx2.ps1 shell            interactive bash in the repo
#
# Requires:
#   - Docker Desktop running.
#   - The Switch 2 devkit drop (ounce-devkit-<date>, containing libounce,
#     portlibs/switch2 and switch2vars.sh - NOT shipped with this repo).
#     Found by searching this folder and its parents, or set its path in
#     SWITCH2_DEVKIT. The drop is mounted READ-ONLY: it is never edited.
#
# Output: cpp\FlashNX2.nro (~32 MB). Copy to sd:/switch/ and run from the
# homebrew menu. First `build` auto-builds the image (~1-2 GB, one-time).
param(
    [Parameter(Position = 0)] [string] $Action = "build",
    [switch] $Dev
)
$ErrorActionPreference = "Stop"

$Repo = $PSScriptRoot          # the repo (= the FlashNX fork)

# --- locate the devkit drop -------------------------------------------------
$Devkit = $env:SWITCH2_DEVKIT
if (-not $Devkit) {
    $dir = $Repo
    for ($i = 0; $i -le 4 -and -not $Devkit; $i++) {
        $hit = Get-ChildItem $dir -Directory -Filter "ounce-devkit-*" -ErrorAction SilentlyContinue |
               Sort-Object Name -Descending | Select-Object -First 1
        if ($hit) { $Devkit = $hit.FullName }
        else { $dir = Split-Path $dir -Parent }
    }
}
if (-not $Devkit -or -not (Test-Path (Join-Path $Devkit "switch2vars.sh"))) {
    Write-Error "Switch 2 devkit drop (ounce-devkit-*, with switch2vars.sh) not found. Set `$env:SWITCH2_DEVKIT to its path."
}
$DevkitMount = ($Devkit -replace '\\', '/')

$Image = "ns2-rust-builder"
$mounts = @(
    "-v", "${Repo}:/project",
    "-v", "${DevkitMount}:/devkit:ro",
    "-v", "${DevkitMount}/libounce:/opt/devkitpro/libounce:ro",
    "-v", "${DevkitMount}/portlibs/switch2:/opt/devkitpro/portlibs/switch2:ro"
)
$envs = @("-e", "SWITCH2_DEVKIT=/devkit")

function Assert-Image {
    docker image inspect $Image *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Image $Image not found - building it (one-time, ~5-10 min)..."
        docker build -t $Image (Join-Path $Repo "docker")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

switch ($Action) {
    "image" {
        docker build -t $Image (Join-Path $Repo "docker")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    "build" {
        Assert-Image
        $profile = if ($Dev) { "dev" } else { "release" }
        docker run --rm @envs @mounts -w /project $Image `
            bash -lc "bash scripts/build-ns2.sh $profile"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    "clean" {
        Assert-Image
        docker run --rm @envs @mounts -w /project $Image `
            bash -lc "cd rust && cargo clean; make -C cpp clean; make -C forwarder clean; rm -f cpp/src/flashnx_forwarder.s"
    }
    "shell" {
        Assert-Image
        docker run --rm -it @envs @mounts -w /project $Image bash
    }
    default {
        Write-Host "Unknown action '$Action'. See header comment."
        exit 1
    }
}
