# dev-scripts

Colección de herramientas y scripts de desarrollo. Cada herramienta vive en su carpeta,
con su propio README.

| Herramienta | Descripción | Lenguaje |
|---|---|---|
| [odoo-freeze-repos](odoo-freeze-repos/) | Congela/descongela el `repos.yaml` de Doodba a los commits en disco | Python |
| [odoo-copydb](odoo-copydb/) | Copia una BBDD Odoo (Doodba + docker compose) de un servidor remoto a local por SSH, con o sin filestore | Bash |

## Instalación

Cada herramienta lleva su `install.sh`, que decide cómo instalarse (normalmente un enlace en
`~/.local/bin`, o en `$BIN_DIR` si lo defines). El `install.sh` raíz ejecuta los de las
herramientas que indiques:

```bash
./install.sh                  # pide confirmación e instala todas
./install.sh odoo-freeze-repos odoo-copydb   # solo las indicadas
```

## Añadir una herramienta

1. Crear la carpeta `nombre-herramienta/` con su `README.md` y su `install.sh`.
2. Añadir una fila a la tabla de arriba.
