#!/usr/bin/env bash
# Enlaza en BIN_DIR (por defecto ~/.local/bin) el ejecutable de cada herramienta.
#
# Convencion: la herramienta <nombre>/ expone el ejecutable <nombre>, <nombre>.py o
# <nombre>.sh; el enlace se crea sin extension.
#
# Uso: ./install.sh [HERRAMIENTA ...]   (sin argumentos, todas)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

if [[ $# -gt 0 ]]; then
    tools=("$@")
else
    tools=()
    for dir in "$ROOT"/*/; do
        tools+=("$(basename "$dir")")
    done
fi

mkdir -p "$BIN_DIR"

for tool in "${tools[@]}"; do
    dir="$ROOT/$tool"
    if [[ ! -d "$dir" ]]; then
        echo "[WARN] no existe la herramienta: $tool" >&2
        continue
    fi
    found=""
    for candidate in "$dir/$tool" "$dir/$tool.py" "$dir/$tool.sh"; do
        if [[ -f "$candidate" && -x "$candidate" ]]; then
            ln -sfn "$candidate" "$BIN_DIR/$tool"
            echo "$BIN_DIR/$tool -> $candidate"
            found=1
            break
        fi
    done
    [[ -n "$found" ]] || echo "[SKIP] $tool: sin ejecutable $tool[.py|.sh]" >&2
done

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "[AVISO] $BIN_DIR no esta en el PATH" >&2 ;;
esac
