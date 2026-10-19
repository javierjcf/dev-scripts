#!/usr/bin/env bash
# Ejecuta el install.sh de las herramientas indicadas; cada una decide como instalarse
# (normalmente un enlace en BIN_DIR, por defecto ~/.local/bin).
#
# Uso: ./install.sh [HERRAMIENTA ...]
#      Sin argumentos pide confirmacion y las instala todas.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

if [[ $# -gt 0 ]]; then
    tools=("$@")
else
    tools=()
    for script in "$ROOT"/*/install.sh; do
        [[ -f "$script" ]] && tools+=("$(basename "$(dirname "$script")")")
    done
    echo "Se instalaran: ${tools[*]}"
    read -r -p "¿Continuar? [s/N] " answer || answer=""
    [[ "$answer" =~ ^[sSyY]$ ]] || { echo "Cancelado."; exit 1; }
fi

for tool in "${tools[@]}"; do
    script="$ROOT/$tool/install.sh"
    if [[ ! -f "$script" ]]; then
        echo "[WARN] $tool: no tiene install.sh" >&2
        continue
    fi
    echo "== $tool"
    bash "$script"
done

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "[AVISO] $BIN_DIR no esta en el PATH" >&2 ;;
esac
