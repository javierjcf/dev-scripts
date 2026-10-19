#!/usr/bin/env bash
# Enlaza odoo-prod2local en BIN_DIR (por defecto ~/.local/bin).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"
ln -sfn "$DIR/odoo-prod2local.sh" "$BIN_DIR/odoo-prod2local"
echo "$BIN_DIR/odoo-prod2local -> $DIR/odoo-prod2local.sh"
