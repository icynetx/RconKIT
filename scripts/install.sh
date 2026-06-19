#!/usr/bin/env sh
set -eu

REPO_URL="${RECONKIT_REPO_URL:-https://github.com/icynetx/RconKIT.git}"
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
ensure_command git git "Install git first, then rerun this command."

mkdir -p "$(dirname "$INSTALL_DIR")"
if [ -d "$INSTALL_DIR/.git" ]; then
  say "[*] Updating existing ReconKit checkout: $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
elif [ -e "$INSTALL_DIR" ]; then
  say "[!] Install path exists but is not a git checkout: $INSTALL_DIR"
  say "    Set RECONKIT_HOME to another path or remove that directory."
  exit 1
else
  say "[*] Cloning ReconKit into $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
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
