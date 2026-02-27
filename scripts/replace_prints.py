"""
Safe script to replace print() calls with logger.info() across the repository.
Usage:
  python scripts/replace_prints.py --dry-run   # show files and counts, do not modify
  python scripts/replace_prints.py --apply     # modify files in place (backups created)

Notes:
- This is a heuristic tool. Review changes and run tests after applying.
- Backups are created as <file>.bak
"""
import argparse
import os
import re
from pathlib import Path

PY_EXT = ".py"

PRINT_RE = re.compile(r"(^|[^\w])print\(")

LOGGER_SNIPPET = "import logging\nlogger = logging.getLogger(__name__)\n"

SKIP_DIRS = {".git", "node_modules", "venv", "env", "__pycache__", "frontend/node_modules"}


def should_skip(path: Path):
    parts = {p.name for p in path.parts}
    return bool(parts & SKIP_DIRS)


def add_logger_header(lines):
    # Insert logger import after shebang or encoding declarations if present.
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # skip future: if file already has 'logger = ' or 'import logging' don't add
    text = "\n".join(lines[:20])
    if "logger =" in text or "import logging" in text:
        return lines
    new_lines = lines[:insert_at] + LOGGER_SNIPPET.splitlines() + [""] + lines[insert_at:]
    return new_lines


def process_file(path: Path, apply: bool):
    s = path.read_text(encoding='utf-8')
    if 'print(' not in s:
        return 0
    lines = s.splitlines()
    new_lines = []
    count = 0
    for line in lines:
        if 'print(' in line:
            # naive replacement: preserve indentation
            indent = re.match(r"^(\s*)", line).group(1)
            # handle common cases where print is used with file= or end= etc; we keep args intact
            replaced = line.replace('print(', 'logger.info(')
            new_lines.append(replaced)
            count += 1
        else:
            new_lines.append(line)
    if count == 0:
        return 0
    # ensure logger header present
    new_lines = add_logger_header(new_lines)
    new_text = "\n".join(new_lines) + "\n"
    if apply:
        bak = path.with_suffix(path.suffix + '.bak')
        if not bak.exists():
            path.replace(bak)
            bak.write_text(s, encoding='utf-8')
            # restore original from bak since replace moved file
            path.write_text(new_text, encoding='utf-8')
        else:
            # if bak exists, just overwrite file
            path.write_text(new_text, encoding='utf-8')
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes')
    parser.add_argument('--root', default='.', help='Repository root')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    py_files = list(root.rglob('*.py'))
    total_files = 0
    total_replacements = 0
    changes = []
    for p in py_files:
        if should_skip(p):
            continue
        # skip this script
        if p.samefile(Path(__file__)):
            continue
        try:
            c = process_file(p, apply=args.apply)
        except Exception as e:
            print(f"Error processing {p}: {e}")
            continue
        if c:
            changes.append((p, c))
            total_files += 1
            total_replacements += c
    print(f"Files changed: {total_files}")
    print(f"Total print() -> logger.info() replacements: {total_replacements}")
    if not args.apply:
        for p, c in changes:
            print(f"  {p}: {c} replacement(s)")
    else:
        print("Backups created with .bak suffix where applicable. Review changes and run tests.")


if __name__ == '__main__':
    main()
