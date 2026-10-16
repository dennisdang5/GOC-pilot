"""Guardrail: src/eval/ must never import the screening/sampling code (src/sampling/)."""

import ast
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1] / "src" / "eval"


def imported_modules(path: Path) -> set[str]:
    mods = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            mods.add(base)
            mods.update(f"{base}.{a.name}" for a in node.names)
    return mods


def test_eval_does_not_import_sampling():
    offenders = [
        (p.name, m)
        for p in EVAL_DIR.rglob("*.py")
        for m in imported_modules(p)
        if "sampling" in m.split(".")
    ]
    assert not offenders, offenders
