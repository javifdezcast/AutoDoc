# !/usr/bin/env python3
"""Extract docstrings from a tree of Python files into a single JSON file.

For every module, class, function, and method that has a docstring, emit:

    {"route": "pkg.module.Class.method", "docstring": "..."}

`route` is the dotted import path of the file (relative to the scan root)
followed by the qualified name of the element inside the file.

Usage:
    python extract_docstrings.py /python -o python_docstrings.json
"""

import argparse
import ast
import json
import os
from pathlib import Path


def module_route(py_file: Path, root: Path) -> str:
    """Turn a .py path into a dotted module route relative to `root`.

    /python/pkg/utils.py     -> pkg.utils
    /python/pkg/__init__.py  -> pkg
    """
    rel = py_file.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect(node, prefix: str, records: list) -> None:
    """Recursively gather (route, docstring) pairs from an AST node.

    Tracking `prefix` as we descend is what lets us build the qualified
    name (Class.method, outer.inner, etc.) that grep cannot recover.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            route = f"{prefix}.{child.name}" if prefix else child.name
            doc = ast.get_docstring(child, clean=True)
            if doc is not None:
                records.append({"route": route, "docstring": doc})
            # descend so we also catch methods, nested functions, inner classes
            collect(child, route, records)


def extract_from_file(py_file: Path, root: Path) -> list:
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    route = module_route(py_file, root)
    records = []

    # module-level docstring (route is just the module path)
    module_doc = ast.get_docstring(tree, clean=True)
    records.append({"route": route, "docstring": module_doc})

    collect(tree, route, records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect docstrings from a Python tree into one JSON file."
    )
    parser.add_argument("root", nargs="?", default="/run/media/javi/ARCH_202501/scc-my-time",
                        help="Root directory to scan (default: /python)")
    parser.add_argument("-o", "--output", default="python_docstrings.json",
                        help="Output JSON file (default: python_docstrings.json)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    all_records = []

    for dirpath, _dirnames, filenames in os.walk(root):
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            py_file = Path(dirpath) / name
            try:
                all_records.extend(extract_from_file(py_file, root))
            except (SyntaxError, UnicodeDecodeError) as exc:
                print(f"skipping {py_file}: {exc}")

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump({"docstrings": all_records}, fh, indent=2, ensure_ascii=False)

    print(f"wrote {len(all_records)} docstrings to {args.output}")


if __name__ == "__main__":
    main()
