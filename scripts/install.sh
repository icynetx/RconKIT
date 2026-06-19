#!/usr/bin/env sh
set -eu

REPO_URL="${RECONKIT_REPO_URL:-https://github.com/icynetx/RconKIT.git}"
ZIP_URL="${RECONKIT_ZIP_URL:-https://github.com/icynetx/RconKIT/archive/refs/heads/main.zip}"
INSTALL_DIR="${RECONKIT_HOME:-$HOME/.reconkit/src}"
INSTALL_OPTIONAL="${RECONKIT_INSTALL_OPTIONAL:-1}"
SKIP_TOOLS="${RECONKIT_SKIP_TOOLS:-0}"

say() { printf '%s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1; }
sudo_cmd() { if [ "$(id -u 2>/dev/null || echo 1)" = "0" ]; then "$@"; elif need sudo; then sudo "$@"; else return 1; fi; }

bootstrap_package() {
  pkg="$1"
  if need apt; then sudo_cmd apt update && sudo_cmd apt install -y "$pkg" && return 0; fi
  if need dnf; then sudo_cmd dnf install -y "$pkg" && return 0; fi
  if need pacman; then sudo_cmd pacman -Sy --needed --noconfirm "$pkg" && return 0; fi
  if need apk; then sudo_cmd apk add "$pkg" && return 0; fi
  if need brew; then brew install "$pkg" && return 0; fi
  return 1
}

ensure_command() {
  cmd="$1"
  pkg="$2"
  hint="$3"
  if need "$cmd"; then return 0; fi
  say "[*] $cmd not found; trying to install $pkg automatically..."
  if bootstrap_package "$pkg" && need "$cmd"; then return 0; fi
  say "[!] $cmd is required. $hint"
  exit 1
}

say "[*] ReconKit installer by Team CynetX"
say "[*] Website: https://cynetx.ir | Telegram: https://t.me/cynetx"

ensure_command python3 python3 "Install Python 3 first, then rerun this command."
if ! need git; then
  say "[*] git not found; trying to install git automatically..."
  bootstrap_package git || true
fi

fetch_zip() {
  tmp_dir="$(mktemp -d 2>/dev/null || mktemp -d -t reconkit)"
  zip_file="$tmp_dir/reconkit.zip"
  say "[*] Downloading ReconKit ZIP fallback"
  if need curl; then curl -fL --connect-timeout 30 --max-time 180 "$ZIP_URL" -o "$zip_file"; else ensure_command wget wget "Install curl or wget first."; wget -O "$zip_file" "$ZIP_URL"; fi
  python3 - "$zip_file" "$INSTALL_DIR" <<'PYZIP'
import shutil
import sys
import zipfile
from pathlib import Path
zip_file = Path(sys.argv[1])
install_dir = Path(sys.argv[2])
tmp_extract = zip_file.parent / "extract"
if install_dir.exists():
    shutil.rmtree(install_dir)
tmp_extract.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(zip_file) as archive:
    archive.extractall(tmp_extract)
roots = [item for item in tmp_extract.iterdir() if item.is_dir()]
if not roots:
    raise SystemExit("ZIP archive did not contain a project directory")
shutil.move(str(roots[0]), str(install_dir))
PYZIP
}

mkdir -p "$(dirname "$INSTALL_DIR")"
if [ -d "$INSTALL_DIR/.git" ]; then
  say "[*] Updating existing ReconKit checkout: $INSTALL_DIR"
  if ! git -C "$INSTALL_DIR" pull --ff-only; then
    say "[!] git pull failed; keeping existing checkout and continuing"
  fi
elif [ -e "$INSTALL_DIR" ]; then
  say "[!] Install path exists but is not a git checkout: $INSTALL_DIR"
  say "    Set RECONKIT_HOME to another path or remove that directory."
  exit 1
else
  say "[*] Cloning ReconKit into $INSTALL_DIR"
  if need git && git clone --depth 1 --single-branch "$REPO_URL" "$INSTALL_DIR"; then
    say "[+] Clone completed"
  else
    say "[!] git clone failed or timed out; trying ZIP fallback"
    fetch_zip
  fi
fi

cd "$INSTALL_DIR"
say "[*] Installing reconkit command for current user"
python3 recon.py --self-install --user

if [ "$SKIP_TOOLS" = "1" ]; then
  say "[*] Skipping external tool installation because RECONKIT_SKIP_TOOLS=1"
else
  if [ "$INSTALL_OPTIONAL" = "1" ]; then
    say "[*] Installing required + optional tools best-effort"
    python3 recon.py --install-deps --with-optional
  else
    say "[*] Installing required tools best-effort"
    python3 recon.py --install-deps
  fi
fi

say "[*] Final dependency status"
python3 recon.py --check-deps || true

say "[+] Done. Try: reconkit"
say "    If your shell cannot find it yet, open a new terminal or run: export PATH=\"$HOME/.local/bin:$PATH\""
