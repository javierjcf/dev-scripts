# dev-scripts

Colección de herramientas y scripts de desarrollo. Cada herramienta vive en su carpeta,
con su propio README.

| Herramienta | Descripción | Lenguaje |
|---|---|---|
| [freeze-doodba](freeze-doodba/) | Congela/descongela el `repos.yaml` de Doodba a los commits en disco | Python |

## Instalación

`install.sh` enlaza (`ln -s`) los ejecutables en `~/.local/bin` (o en `$BIN_DIR`):

```bash
./install.sh                  # todas las herramientas
./install.sh freeze-doodba    # solo algunas
```

## Añadir una herramienta

1. Crear la carpeta `nombre-herramienta/` con su `README.md`.
2. Si debe ir al PATH, que su ejecutable se llame como la carpeta (`nombre-herramienta`, `.py` o `.sh`) y tenga permiso de ejecución.
3. Añadir una fila a la tabla de arriba.
