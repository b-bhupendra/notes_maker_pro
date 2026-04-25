"""
setup_bins.py — Self-bootstrapping binary manager.

Automatically downloads platform-appropriate binaries (ffmpeg, ffprobe)
to `core_engine/bin/` when they are not found on PATH or in the local bin dir.

Binaries are downloaded from the official BtbN GitHub releases (Windows)
and the official ffmpeg.org static builds (Linux/macOS).

The `core_engine/bin/` directory is excluded from git via .gitignore.
"""

import os
import sys
import stat
import shutil
import logging
import zipfile
import tarfile
import platform
import subprocess
import urllib.request
from pathlib import Path

logger = logging.getLogger("engine.setup_bins")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BIN_DIR = Path(__file__).parent.parent / "bin"

# Official BtbN release for Windows (GPL shared, no extra deps)
FFMPEG_WINDOWS_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

# John Van Sickle static builds for Linux
FFMPEG_LINUX_URL = (
    "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
)

# evermeet.cx builds for macOS
FFMPEG_MACOS_URL = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"

REQUIRED_BINS = ["ffmpeg", "ffprobe"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ensure_ffmpeg() -> bool:
    """
    Ensure ffmpeg/ffprobe are available.  Priority order:
      1. Already on system PATH
      2. Already in BIN_DIR
      3. Download and extract to BIN_DIR

    Returns True if ffmpeg is ready, False if download failed.
    """
    if _bins_on_path():
        logger.info("ffmpeg found on system PATH — no download needed.")
        return True

    if _bins_in_local_dir():
        _add_bin_dir_to_path()
        logger.info(f"ffmpeg found in local bin dir: {BIN_DIR}")
        return True

    logger.info("ffmpeg not found — attempting automatic download...")
    return _download_ffmpeg()


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _bins_on_path() -> bool:
    return all(shutil.which(b) is not None for b in REQUIRED_BINS)


def _bins_in_local_dir() -> bool:
    ext = ".exe" if platform.system() == "Windows" else ""
    return all((BIN_DIR / f"{b}{ext}").exists() for b in REQUIRED_BINS)


def _add_bin_dir_to_path():
    bin_str = str(BIN_DIR)
    if bin_str not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")
        logger.info(f"Added {BIN_DIR} to PATH.")


# ---------------------------------------------------------------------------
# Download logic
# ---------------------------------------------------------------------------

def _download_ffmpeg() -> bool:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    system = platform.system()

    try:
        if system == "Windows":
            return _download_windows()
        elif system == "Linux":
            return _download_linux()
        elif system == "Darwin":
            return _download_macos()
        else:
            logger.error(f"Unsupported OS for auto-download: {system}")
            return False
    except Exception as e:
        logger.error(f"ffmpeg auto-download failed: {e}")
        return False


def _reporthook(blocknum, blocksize, totalsize):
    downloaded = blocknum * blocksize
    if totalsize > 0:
        pct = min(100, downloaded * 100 // totalsize)
        print(f"\r  Downloading ffmpeg... {pct}%", end="", flush=True)


def _download_windows() -> bool:
    archive = BIN_DIR / "ffmpeg_win.zip"
    logger.info(f"Downloading Windows ffmpeg from BtbN releases...")
    urllib.request.urlretrieve(FFMPEG_WINDOWS_URL, archive, _reporthook)
    print()  # newline after progress

    with zipfile.ZipFile(archive, "r") as zf:
        # The zip contains a top-level folder; find ffmpeg.exe inside it
        for member in zf.namelist():
            filename = Path(member).name
            if filename in ("ffmpeg.exe", "ffprobe.exe"):
                target = BIN_DIR / filename
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                logger.info(f"Extracted {filename} → {target}")

    archive.unlink()
    _add_bin_dir_to_path()
    return _bins_in_local_dir()


def _download_linux() -> bool:
    archive = BIN_DIR / "ffmpeg_linux.tar.xz"
    logger.info("Downloading Linux ffmpeg static build...")
    urllib.request.urlretrieve(FFMPEG_LINUX_URL, archive, _reporthook)
    print()

    with tarfile.open(archive, "r:xz") as tf:
        for member in tf.getmembers():
            if member.name.endswith(("/ffmpeg", "/ffprobe")):
                member.name = Path(member.name).name  # flatten path
                tf.extract(member, BIN_DIR)
                # Make executable
                (BIN_DIR / member.name).chmod(
                    (BIN_DIR / member.name).stat().st_mode | stat.S_IEXEC
                )
                logger.info(f"Extracted {member.name} → {BIN_DIR}")

    archive.unlink()
    _add_bin_dir_to_path()
    return _bins_in_local_dir()


def _download_macos() -> bool:
    # evermeet.cx only provides ffmpeg; ffprobe ships separately
    for binary in REQUIRED_BINS:
        url = f"https://evermeet.cx/ffmpeg/getrelease/{binary}/zip"
        archive = BIN_DIR / f"{binary}_mac.zip"
        logger.info(f"Downloading macOS {binary}...")
        urllib.request.urlretrieve(url, archive, _reporthook)
        print()

        with zipfile.ZipFile(archive, "r") as zf:
            for name in zf.namelist():
                if name == binary:
                    zf.extract(name, BIN_DIR)
                    target = BIN_DIR / name
                    target.chmod(target.stat().st_mode | stat.S_IEXEC)
                    logger.info(f"Extracted {binary} → {target}")

        archive.unlink()

    _add_bin_dir_to_path()
    return _bins_in_local_dir()


# ---------------------------------------------------------------------------
# CLI entry-point for manual setup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    success = ensure_ffmpeg()
    if success:
        print("✅ ffmpeg is ready.")
        sys.exit(0)
    else:
        print("❌ ffmpeg setup failed. Check logs above.")
        sys.exit(1)
