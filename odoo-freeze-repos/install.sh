#!/usr/bin/env bash
# Enlaza odoo-freeze-repos en BIN_DIR (por defecto ~/.local/bin).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sfn "$DIR/odoo-freeze-repos.py" "$BIN_DIR/odoo-freeze-repos"
echo "$BIN_DIR/odoo-freeze-repos -> $DIR/odoo-freeze-repos.py"
