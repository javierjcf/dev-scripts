# freeze-doodba

Congela y descongela el `repos.yaml` de un proyecto [Doodba](https://github.com/Tecnativa/doodba)
a los commits que ya hay en disco, para que el siguiente `invoke git-aggregate` descargue
exactamente el mismo código.

Solo usa la librería estándar de Python 3 (sin PyYAML ni venv).

## Uso

```bash
freeze-doodba freeze   RUTA [REPO,REPO ...]
freeze-doodba unfreeze RUTA [REPO,REPO ...]
freeze-doodba list     RUTA [REPO,REPO ...]
```

`RUTA` es la raíz del proyecto Doodba (donde están `common.yaml` y `odoo/`). Sin `REPO` actúa
sobre todos los repos con `.git` bajo `odoo/custom/src/` (excepto `private/`). `REPO` admite
nombres separados por comas o espacios.

| Comando | Qué hace |
|---|---|
| `freeze` | Sustituye cada ref de `merges` por su SHA y deja la ref original en `#frozen:<ref>`. Los repos que no estaban en `repos.yaml` se añaden al final, tras una línea de marca. Escribe la fecha y hora en la primera línea |
| `unfreeze` | Devuelve cada SHA con `#frozen:` a su ref; un SHA sin marca (fijado a mano) pasa a `target` si es el primer merge; elimina los repos añadidos tras la marca |
| `list` | Muestra fecha, hash y mensaje del commit actual de cada repo |

## Ficheros de respaldo

Se crean en `odoo/custom/src/`:

| Fichero | Contenido | Cuándo se escribe |
|---|---|---|
| `bck-repos.yaml` | El **original**, antes del primer `freeze` | Solo si no existe. Nunca se sobrescribe; para empezar de cero, bórralo |
| `frozen-repos.yaml` | El **último estado congelado** | En cada `unfreeze`, antes de descongelar |

Para volver atrás se copia a mano el que corresponda sobre `repos.yaml`:

```bash
cp odoo/custom/src/frozen-repos.yaml odoo/custom/src/repos.yaml   # retomar el último congelado
cp odoo/custom/src/bck-repos.yaml    odoo/custom/src/repos.yaml   # volver al original
```

## Flujo típico

1. `freeze-doodba freeze /ruta/doodba`: se guarda el original y se fijan los SHAs.
2. Más adelante, `freeze-doodba unfreeze /ruta/doodba` y `invoke git-aggregate` para traer lo último.
3. `freeze-doodba freeze /ruta/doodba` otra vez: el original no se toca.

## Limitaciones

- El lector de YAML es mínimo (mapas, listas, comentarios, bloques `|`). No soporta anclas ni estilo `{}`/`[]`.
- `unfreeze` no conserva los pines manuales de `repos.yaml`; solo quedan en `bck-repos.yaml`.
- El SHA de los PRs fijados se localiza por el mensaje del merge commit que dejó git-aggregator.
