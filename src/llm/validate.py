"""Evidence-span check: is the model's quote really in the note?

A span is verified when its whitespace-normalized form is an exact (case-sensitive) substring of
the whitespace-normalized note. [** **] de-identification placeholders are left as they are, the
same for every method. The runner fills span_verified when it writes each prediction.

Run from the repo root:  python -m src.llm.validate [PREDICTION_FILES...]
Prints per file: records, errors, spans given, % spans verified. Never prints spans.
"""

import re
import sys
from pathlib import Path

from src.llm.schema import Prediction

ROOT = Path(__file__).resolve().parents[2]
PRED_DIR = ROOT / "data" / "predictions"

_WS = re.compile(r"\s+")


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text).strip()


def span_verified(span: str | None, note: str) -> bool | None:
    """True / False for a non-empty span, None when the model gave no span."""
    if span is None or not span.strip():
        return None
    return normalize_ws(span) in normalize_ws(note)


def read_predictions(path: Path) -> dict[int, Prediction]:
    """Latest record per ROW_ID (files are append-only)."""
    latest = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                p = Prediction.model_validate_json(line)
                latest[p.row_id] = p
    return latest


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]] or sorted(PRED_DIR.glob("*.jsonl"))
    if not paths:
        print(f"validate: no prediction files in {PRED_DIR.as_posix()}/")
        return 1
    print(f"{'file':<40}{'n':>5}{'errors':>8}{'spans':>7}{'verified':>10}")
    for path in paths:
        preds = list(read_predictions(path).values())
        errors = sum(p.error is not None for p in preds)
        checked = [p.span_verified for p in preds if p.span_verified is not None]
        rate = f"{sum(checked) / len(checked):.0%}" if checked else "-"
        print(f"{path.name:<40}{len(preds):>5}{errors:>8}{len(checked):>7}{rate:>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
