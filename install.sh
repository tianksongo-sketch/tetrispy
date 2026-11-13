#!/usr/bin/env bash
# Installs the "load" and "run" commands.
#   curl -fsSL https://raw.githubusercontent.com/tianksongo-sketch/tetrispy/main/install.sh | bash
# or after git clone:
#   bash tetrispy/install.sh
set -eu

GH_USER="tianksongo-sketch"
REPO="tetrispy"
RAW="https://raw.githubusercontent.com/$GH_USER/$REPO/main"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$BIN_DIR"

# If this script sits next to a 'load' file (git clone), copy it; otherwise download it.
SELF="${BASH_SOURCE[0]:-}"
SRC_DIR=""
if [ -n "$SELF" ] && [ -f "$(dirname "$SELF")/load" ]; then
  SRC_DIR="$(dirname "$SELF")"
fi

if [ -n "$SRC_DIR" ]; then
  cp "$SRC_DIR/load" "$BIN_DIR/load"
else
  command -v curl >/dev/null 2>&1 || { echo "curl is required."; exit 1; }
  curl -fsSL "$RAW/load" -o "$BIN_DIR/load"
fi
chmod +x "$BIN_DIR/load"
echo "Installed: $BIN_DIR/load"

# Put $BIN_DIR on PATH in future shells. Login shells (Arch, macOS Terminal)
# read .bash_profile, interactive shells read .bashrc, so write to both.
line='export PATH="$HOME/.local/bin:$PATH"'
rcs="$HOME/.bashrc $HOME/.bash_profile"
case "${SHELL:-}" in *zsh*) rcs="$rcs $HOME/.zshrc" ;; esac
for rc in $rcs; do
  if ! grep -qsF '.local/bin' "$rc" 2>/dev/null; then
    printf '%s\n' "$line" >> "$rc"
    echo "PATH updated in $rc"
  fi
done

echo
echo "Done. Type:  load tetris"
echo "(in the current terminal only, you can also run: $line)"
