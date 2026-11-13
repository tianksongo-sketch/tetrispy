#!/usr/bin/env bash
# Installs the "load" and "run" commands. Run once, either way:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/games/main/install.sh | bash
#   git clone https://github.com/YOUR_GITHUB_USERNAME/games && bash games/install.sh
set -eu

GH_USER="YOUR_GITHUB_USERNAME"
REPO="games"
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

# Make $BIN_DIR part of PATH in future shells (added once).
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    case "${SHELL:-}" in
      *zsh) rc="$HOME/.zshrc" ;;
      *)    rc="$HOME/.bashrc" ;;
    esac
    if ! grep -qsF "$BIN_DIR" "$rc" 2>/dev/null; then
      echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$rc"
    fi
    echo "PATH updated in $rc"
    ;;
esac

echo "Done. Open a new terminal, then type:  load tetris   and then:  run"
