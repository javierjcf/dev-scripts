#!/usr/bin/env python3
"""Congela/descongela el repos.yaml de un proyecto Doodba a los commits ya existentes en disco.

Uso:
    odoo-freeze-repos freeze   RUTA [REPO,REPO ...]
    odoo-freeze-repos unfreeze RUTA [REPO,REPO ...]
    odoo-freeze-repos list     RUTA [REPO,REPO ...]

RUTA es la raiz del proyecto Doodba (donde estan common.yaml y odoo/). Sin REPO actua
sobre todos los repos con .git bajo odoo/custom/src/ (excluyendo siempre private/).
REPO admite nombres separados por comas o espacios.

freeze: sustituye cada ref de 'merges' por su SHA y deja la ref original en un comentario
('#frozen:<ref>'). Los repos que no estaban en repos.yaml se anaden al final, tras una
linea de marca. Antes de tocar nada guarda el estado original en bck-repos.yaml, solo si
ese fichero no existe (nunca lo sobrescribe: para empezar de cero, borralo).

En la primera linea de repos.yaml queda la fecha y hora del ultimo freeze (unfreeze la quita).

unfreeze: deja repos.yaml como antes de congelar. Cada SHA con '#frozen:' recupera su ref;
un SHA sin marca (p. ej. uno fijado a mano) se vuelve 'target' si es el primer merge; y los
repos anadidos tras la marca se eliminan. Antes copia el estado congelado a
frozen-repos.yaml. bck-repos.yaml se conserva.
"""
import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path



class Project:
    """Rutas de un proyecto Doodba a partir de su carpeta raiz."""

    def __init__(self, root):
        self.root = root
        self.src = root / "odoo" / "custom" / "src"
        self.repos_yaml = self.src / "repos.yaml"
        self.backup_yaml = self.src / "bck-repos.yaml"
        self.frozen_yaml = self.src / "frozen-repos.yaml"
        self.common_yaml = root / "common.yaml"

    def rel(self, path):
        return path.relative_to(self.root)

    def validate(self, need_common):
        missing = [str(p) for p in (self.src, self.repos_yaml) if not p.exists()]
        if need_common and not self.common_yaml.exists():
            missing.append(str(self.common_yaml))
        if missing:
            sys.exit(f"{self.root} no parece un proyecto Doodba; falta: " + ", ".join(missing))


def load_project(root_arg, need_common):
    root = Path(root_arg).expanduser().resolve()
    project = Project(root)
    project.validate(need_common)
    return project


def run_git(repo_path, *args):
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def is_sha(ref):
    return len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower())


def discover_repos(project):
    return sorted(
        d.name
        for d in project.src.iterdir()
        if d.is_dir() and d.name != "private" and (d / ".git").is_dir()
    )


def normalize_key(key):
    return key[2:] if key.startswith("./") else key


def repo_key(data, name):
    """Devuelve la clave tal cual aparece en el dict ('name' o './name')."""
    for key in data:
        if normalize_key(key) == name:
            return key
    return None


def _strip_comment(text):
    """Quita el comentario ' #...' final respetando comillas."""
    quote = None
    for i, c in enumerate(text):
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i]
    return text


def _scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def _parse_block(items, pos, indent):
    """Parsea mapas y listas de escalares por indentacion. Devuelve (valor, nueva_pos)."""
    if items[pos][1].startswith("- ") or items[pos][1] == "-":
        result = []
        while pos < len(items) and items[pos][0] == indent and items[pos][1].startswith("-"):
            result.append(_scalar(items[pos][1][1:]))
            pos += 1
        return result, pos
    result = {}
    while pos < len(items) and items[pos][0] == indent:
        key, sep, rest = items[pos][1].partition(":")
        if not sep:
            sys.exit(f"YAML no soportado: '{items[pos][1]}'")
        key, rest = _scalar(key), rest.strip()
        pos += 1
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            while pos < len(items) and items[pos][0] > indent:
                pos += 1  # texto de bloque: no hace falta su contenido
            result[key] = ""
        elif rest:
            result[key] = _scalar(rest)
        elif pos < len(items) and (items[pos][0] > indent or (items[pos][0] == indent and items[pos][1].startswith("-"))):
            result[key], pos = _parse_block(items, pos, items[pos][0])
        else:
            result[key] = None
    return result, pos


def load_yaml(path):
    """Lector YAML minimo (stdlib): mapas, listas de escalares y comentarios.

    Cubre repos.yaml y common.yaml de Doodba; no soporta anclas ni estilo flow.
    """
    items = []
    block_indent = None  # indentacion del padre de un bloque literal '|' en curso
    for raw in path.read_text(encoding="utf-8").splitlines():
        indent = len(raw) - len(raw.lstrip(" "))
        if block_indent is not None:
            if not raw.strip() or indent > block_indent:
                continue
            block_indent = None
        text = _strip_comment(raw).strip()
        if not text or text == "---":
            continue
        items.append((indent, text))
        if re.search(r":\s*[|>][+-]?$", text):
            block_indent = indent
    if not items:
        return {}
    return _parse_block(items, 0, items[0][0])[0]


def read_lines(path):
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def write_lines(path, lines):
    path.write_text("".join(lines), encoding="utf-8")


# Clave de nivel superior tipo "./odoo:" o "account-reconcile:" (nunca indentada ni comentada).
TOP_KEY_RE = re.compile(r"^(?!\s)(?!#)(\S.*):\s*$")


def find_block(lines, name):
    """Devuelve (start, end) de las lineas del bloque de nivel superior de `name`, o None."""
    start = None
    for i, line in enumerate(lines):
        m = TOP_KEY_RE.match(line)
        if m and normalize_key(m.group(1)) == name:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if TOP_KEY_RE.match(lines[j]):
            end = j
            break
    return start, end


def find_merge_line(block_lines, old_value):
    """Indice de la linea '- <old_value>' (con comentario opcional detras); ignora lineas comentadas."""
    for idx, line in enumerate(block_lines):
        m = re.match(r"\s*-\s+(.+?)\s*(?:#.*)?$", line)
        if m and m.group(1) == old_value:
            return idx
    return None


def synthesize_entry(repo_path):
    """Entrada minima para un repo que hoy depende del auto-generado via addons.yaml."""
    url = run_git(repo_path, "config", "--get", "remote.origin.url")
    return {
        "defaults": {"depth": "$DEPTH_MERGE"},
        "remotes": {"origin": url},
        "target": "origin $ODOO_VERSION",
        "merges": ["origin $ODOO_VERSION"],
    }


def get_odoo_version(project):
    common_yaml = load_yaml(project.common_yaml)
    try:
        return str(common_yaml["services"]["odoo"]["build"]["args"]["ODOO_VERSION"])
    except (KeyError, TypeError):
        sys.exit(f"{project.common_yaml} no define services.odoo.build.args.ODOO_VERSION")


def resolve_ref(repo_path, remote, ref, odoo_version):
    """Resuelve (remote, ref) al commit que representa hoy, sin red.

    Dos estrategias, en orden:
    1. Rama normal ya trackeada localmente (<remote>/<rama>) -> exacta y sin ambiguedad.
    2. Ref puntual (PR, etc.) que git-aggregator fusiono en su dia: se busca el merge
       commit cuyo mensaje menciona esa ref exacta ("Merge commit '<ref>' of ... into
       ...") y se toma su segundo padre. Se usa el mas reciente si hay varios.
    """
    branch = ref.replace("$ODOO_VERSION", odoo_version)
    try:
        sha = run_git(repo_path, "rev-parse", "--verify", "--quiet", f"{remote}/{branch}")
        return sha, None
    except subprocess.CalledProcessError:
        pass

    try:
        log = run_git(repo_path, "log", "--first-parent", "--merges", "--format=%H\t%s")
    except subprocess.CalledProcessError as exc:
        return None, f"error ejecutando git log ({exc})"

    for line in log.splitlines():
        sha, _, subject = line.partition("\t")
        if f"'{ref}'" in subject:
            try:
                return run_git(repo_path, "rev-parse", f"{sha}^2"), None
            except subprocess.CalledProcessError as exc:
                return None, f"no se pudo resolver el segundo padre de {sha[:10]} ({exc})"

    return None, f"no se encontro ningun merge commit que mencione '{ref}'"


def resolve_merges(name, repo_path, merges, odoo_version):
    """Resuelve cada entrada de forma independiente. Las que fallen quedan sin tocar."""
    resolved = list(merges)
    warnings = []
    for i, m in enumerate(merges):
        remote, ref = m.split(None, 1)
        if is_sha(ref):
            continue  # ya fijado a mano
        sha, err = resolve_ref(repo_path, remote, ref, odoo_version)
        if sha is None:
            warnings.append(f"{name}: merges[{i}] ('{m}') no se pudo resolver: {err}")
            continue
        resolved[i] = f"{remote} {sha}"
    return resolved, warnings


def validate_targets(requested, all_repos):
    if not requested:
        return all_repos
    valid = []
    for name in requested:
        if name not in all_repos:
            print(f"[WARN] repo desconocido o sin .git: {name}", file=sys.stderr)
            continue
        valid.append(name)
    return valid


ADDED_MARKER = (
    "# --- A partir de aqui: repos anadidos por odoo-freeze-repos, antes implicitos "
    "via addons.yaml ---\n"
)
# Marca del nombre anterior del script: se sigue reconociendo en repos.yaml ya congelados.
LEGACY_ADDED_MARKER = ADDED_MARKER.replace("odoo-freeze-repos", "freeze_repos.py")


def ensure_added_marker(lines):
    """Inserta el comentario separador una unica vez, si todavia no esta."""
    if find_added_marker(lines) is not None:
        return
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    lines.append("\n")
    lines.append(ADDED_MARKER)


def append_new_block(lines, name, url, sha):
    ensure_added_marker(lines)
    lines.append("\n")
    lines.append(f"{name}:\n")
    lines.append("  defaults:\n")
    lines.append("    depth: $DEPTH_MERGE\n")
    lines.append("  remotes:\n")
    lines.append(f"    origin: {url}\n")
    lines.append("  target: origin $ODOO_VERSION\n")
    lines.append("  merges:\n")
    lines.append(f"    - origin {sha}  #frozen:$ODOO_VERSION\n")


STAMP_PREFIX = "# Congelado con odoo-freeze-repos el "
LEGACY_STAMP_PREFIX = "# Congelado con freeze_repos.py el "  # nombre anterior del script
STAMP_PREFIXES = (STAMP_PREFIX, LEGACY_STAMP_PREFIX)


def set_stamp(lines):
    """Pone (o actualiza) en la primera linea la fecha y hora del freeze."""
    stamp = f"{STAMP_PREFIX}{datetime.datetime.now():%Y-%m-%d %H:%M}\n"
    if lines and lines[0].startswith(STAMP_PREFIXES):
        lines[0] = stamp
    else:
        lines.insert(0, stamp)


def remove_stamp(lines):
    if lines and lines[0].startswith(STAMP_PREFIXES):
        del lines[0]


def cmd_freeze(args):
    project = args.project
    all_repos = discover_repos(project)
    targets = validate_targets(args.repos, all_repos)
    if not targets:
        print("Nada que congelar.")
        return

    data = load_yaml(project.repos_yaml)
    lines = read_lines(project.repos_yaml)
    odoo_version = get_odoo_version(project)

    added = []
    changed = []
    skipped = []

    for name in targets:
        repo_path = project.src / name
        key = repo_key(data, name)
        is_new = key is None
        entry = synthesize_entry(repo_path) if is_new else data[key]

        merges = entry.get("merges") or []
        if not merges:
            skipped.append(f"{name}: sin 'merges' definido")
            continue

        resolved, warns = resolve_merges(name, repo_path, merges, odoo_version)
        skipped.extend(warns)

        if resolved == merges:
            continue  # nada resuelto (o ya estaba todo fijado)

        if is_new:
            url = entry["remotes"]["origin"]
            sha = resolved[0].split(" ", 1)[1]
            append_new_block(lines, name, url, sha)
            added.append((name, resolved))
            continue

        block_range = find_block(lines, name)
        if block_range is None:
            skipped.append(f"{name}: no se localizo su bloque en repos.yaml")
            continue
        start, end = block_range
        block_lines = lines[start:end]

        for old_value, new_value in zip(merges, resolved):
            if old_value == new_value:
                continue
            idx = find_merge_line(block_lines, old_value)
            if idx is None:
                skipped.append(f"{name}: no se localizo la linea de merge '{old_value}', no se toca")
                continue
            block_lines[idx] = block_lines[idx].replace(
                old_value, f"{new_value}  #frozen:{old_value.split(None, 1)[1]}", 1
            )

        lines[start:end] = block_lines
        changed.append((name, resolved))

    if not added and not changed:
        print("Nada que congelar (todo ya estaba fijado o no se pudo resolver con seguridad).")
        if skipped:
            print("\nAvisos:")
            for msg in skipped:
                print(f"  - {msg}")
        return

    set_stamp(lines)
    backup_created = not project.backup_yaml.exists()
    if backup_created:
        shutil.copy2(project.repos_yaml, project.backup_yaml)
    write_lines(project.repos_yaml, lines)

    if changed:
        print("\nActualizados:")
        for name, resolved in changed:
            print(f"  {name}: " + ", ".join(m.split(" ", 1)[1][:10] for m in resolved))
    if added:
        print("\nNuevos (antes implicitos via addons.yaml):")
        for name, resolved in added:
            print(f"  {name}: " + ", ".join(m.split(" ", 1)[1][:10] for m in resolved))
    if skipped:
        print("\nOmitidos:")
        for msg in skipped:
            print(f"  {msg}")
    if backup_created:
        print(f"\nrepos.yaml congelado; original guardado en {project.rel(project.backup_yaml)}")
    else:
        print(f"\nrepos.yaml congelado; el original ya estaba en {project.rel(project.backup_yaml)} (no se toca)")


def find_added_marker(lines):
    for i, line in enumerate(lines):
        if line in (ADDED_MARKER, LEGACY_ADDED_MARKER):
            return i
    return None


def cmd_unfreeze(args):
    project = args.project
    data = load_yaml(project.repos_yaml)
    lines = read_lines(project.repos_yaml)
    original_lines = list(lines)

    targets = args.repos or sorted(normalize_key(k) for k in data)
    marker_idx = find_added_marker(lines)
    restored = []
    removed = []
    skipped = []

    for name in targets:
        key = repo_key(data, name)
        block_range = find_block(lines, name) if key is not None else None
        if block_range is None:
            skipped.append(f"{name}: sin entrada en repos.yaml")
            continue
        start, end = block_range

        # Repos anadidos por freeze (tras la marca): se eliminan, no se descongelan.
        if marker_idx is not None and start > marker_idx:
            del lines[start:end]
            removed.append(name)
            continue

        block_lines = lines[start:end]
        entry = data[key]
        touched = False

        for i, value in enumerate(entry.get("merges") or []):
            remote, ref = value.split(None, 1)
            if not is_sha(ref):
                continue
            idx = find_merge_line(block_lines, value)
            if idx is None:
                continue
            marker = re.search(re.escape(value) + r"\s+#frozen:(\S+)", block_lines[idx])
            if marker:
                block_lines[idx] = block_lines[idx].replace(marker.group(0), f"{remote} {marker.group(1)}", 1)
                touched = True
            elif i == 0 and entry.get("target"):
                # SHA sin marca (fijado a mano): la base es siempre 'target'.
                block_lines[idx] = block_lines[idx].replace(value, entry["target"], 1)
                touched = True
            else:
                skipped.append(f"{name}: '{value}' sin ref original, restauralo a mano")

        if touched:
            lines[start:end] = block_lines
            restored.append(name)

    # Si ya no queda ningun repo anadido, se quita tambien la marca y el hueco que dejo freeze.
    if marker_idx is not None:
        tail = lines[marker_idx + 1:]
        if not any(TOP_KEY_RE.match(line) for line in tail):
            del lines[marker_idx:]
            if lines and not lines[-1].strip():
                lines.pop()

    if not any("#frozen:" in line for line in lines):
        remove_stamp(lines)  # ya no queda nada congelado

    if lines == original_lines:
        print("Nada que descongelar.")
    else:
        shutil.copy2(project.repos_yaml, project.frozen_yaml)
        write_lines(project.repos_yaml, lines)
        if restored:
            print("Descongelados: " + ", ".join(restored))
        if removed:
            print("Eliminados (anadidos por freeze): " + ", ".join(removed))
        print(f"Estado congelado guardado en {project.rel(project.frozen_yaml)}")
        print(f"Original (antes del primer freeze) en {project.rel(project.backup_yaml)}")
        print("Ahora ejecuta 'invoke git-aggregate' para traer lo ultimo antes de volver a congelar.")
    if skipped:
        print("\nAvisos:")
        for msg in skipped:
            print(f"  - {msg}")


def cmd_list(args):
    project = args.project
    all_repos = discover_repos(project)
    targets = validate_targets(args.repos, all_repos)
    if not targets:
        print("Nada que listar.")
        return

    rows = []
    for name in targets:
        repo_path = project.src / name
        try:
            info = run_git(repo_path, "log", "-1", "--date=short", "--format=%cd\t%h\t%s")
        except subprocess.CalledProcessError as exc:
            rows.append((name, "?", "?", f"[error: {exc}]"))
            continue
        date, short_sha, subject = info.split("\t", 2)
        rows.append((name, date, short_sha, subject))

    name_w = max(len(r[0]) for r in rows)
    for name, date, short_sha, subject in rows:
        print(f"{name:<{name_w}}  {date}  {short_sha}  {subject}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("root", metavar="RUTA", help="Raiz del proyecto Doodba (donde estan common.yaml y odoo/)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_freeze = sub.add_parser("freeze", parents=[common], help="Fija repos.yaml a los commits actuales (guarda bck-repos.yaml si no existe)")
    p_freeze.add_argument("repos", nargs="*", metavar="REPO", help="Carpetas a congelar, separadas por comas (por defecto: todas)")

    p_unfreeze = sub.add_parser("unfreeze", parents=[common], help="Devuelve repos.yaml a sus refs flotantes (guarda frozen-repos.yaml)")
    p_unfreeze.add_argument("repos", nargs="*", metavar="REPO", help="Carpetas a descongelar, separadas por comas (por defecto: todas)")

    p_list = sub.add_parser("list", parents=[common], help="Muestra fecha, hash y mensaje del commit actual de cada repo")
    p_list.add_argument("repos", nargs="*", metavar="REPO", help="Carpetas a listar, separadas por comas (por defecto: todas)")

    args = parser.parse_args()
    args.repos = [r for value in args.repos for r in value.split(",") if r]
    args.project = load_project(args.root, need_common=args.command == "freeze")

    if args.command == "freeze":
        cmd_freeze(args)
    elif args.command == "unfreeze":
        cmd_unfreeze(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
