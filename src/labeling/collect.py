"""Validate returned label files and check coverage against the assignments.

Run from anywhere:  python -m src.labeling.collect

Reads data/assignments/*.parquet and data/labels/*.jsonl. For each label file: schema-validates
every line (latest record per ROW_ID wins) and reports labeled / missing / extra ROW_IDs.
Prints counts, ROW_IDs, line numbers and error locations only.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from src.labeling.schema import GOCLabel

ROOT = Path(__file__).resolve().parents[2]
ASSIGN_DIR = ROOT / "data" / "assignments"
LABEL_DIR = ROOT / "data" / "labels"


def read_labels(path: Path) -> tuple[dict[int, GOCLabel], list[str]]:
    """Latest valid label per ROW_ID, plus problems as 'line N: location/type' strings."""
    latest, problems = {}, []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            label = GOCLabel.model_validate(json.loads(line))
        except json.JSONDecodeError:
            problems.append(f"line {n}: not valid JSON")
            continue
        except ValidationError as e:
            locs = ", ".join(".".join(map(str, err["loc"])) or err["type"] for err in e.errors())
            problems.append(f"line {n}: invalid ({locs})")
            continue
        latest[label.row_id] = label
    return latest, problems


def main() -> int:
    assignments = {p.stem: set(pd.read_parquet(p)["ROW_ID"]) for p in ASSIGN_DIR.glob("*.parquet")}
    label_files = sorted(LABEL_DIR.glob("*.jsonl"))
    if not label_files:
        print(f"collect: no label files in {LABEL_DIR.relative_to(ROOT).as_posix()}/")
        return 1
    covered: dict[str, set[int]] = {name: set() for name in assignments}
    ok = True
    for path in label_files:
        latest, problems = read_labels(path)
        names = {lab.assignment for lab in latest.values()}
        print(f"{path.name}: {len(latest)} labeled, {len(problems)} problem lines")
        for p in problems:
            print(f"  {p}")
            ok = False
        for name in names:
            if name not in assignments:
                print(f"  unknown assignment {name!r}")
                ok = False
                continue
            ids = {r for r, lab in latest.items() if lab.assignment == name}
            extra = ids - assignments[name]
            if extra:
                print(f"  {len(extra)} ROW_IDs not in {name}: {sorted(extra)}")
                ok = False
            covered[name] |= ids & assignments[name]
    print()
    for name, ids in sorted(assignments.items()):
        missing = ids - covered[name]
        status = "complete" if not missing else f"{len(missing)} missing"
        print(f"{name:<16}{len(covered[name]):>3} / {len(ids):<3} {status}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
