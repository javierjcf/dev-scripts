# dev-scripts

Colección de herramientas y scripts de desarrollo. Cada herramienta vive en su carpeta,
con su propio README.

| Herramienta | Descripción | Lenguaje |
|---|---|---|
| [odoo-freeze-repos](odoo-freeze-repos/) | Congela/descongela el `repos.yaml` de Doodba a los commits en disco | Python |

## Instalación

Cada herramienta lleva su `install.sh`, que decide cómo instalarse (normalmente un enlace en
`~/.local/bin`, o en `$BIN_DIR` si lo defines). El `install.sh` raíz ejecuta los de las
herramientas que indiques:

```bash
./install.sh                  # pide confirmación e instala todas
./install.sh odoo-freeze-repos    # solo las indicadas
```

## Añadir una herramienta

1. Crear la carpeta `nombre-herramienta/` con su `README.md` y su `install.sh`.
2. Añadir una fila a la tabla de arriba.
