#!/usr/bin/env bash
# Enlaza odoo-copydb en BIN_DIR (por defecto ~/.local/bin).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sfn "$DIR/odoo-copydb.sh" "$BIN_DIR/odoo-copydb"
echo "$BIN_DIR/odoo-copydb -> $DIR/odoo-copydb.sh"
