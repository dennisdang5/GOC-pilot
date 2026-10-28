"""Note loading for the LLM runner. Returns note text in memory only; never prints it.

Sets map to the frozen sample files: dev, test_a (test_sample) and test_b (test_b_sample).
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
SAMPLES = {"dev": "dev_sample.parquet", "test_a": "test_sample.parquet",
           "test_b": "test_b_sample.parquet"}


def set_row_ids(set_name: str, derived: Path = DERIVED) -> list[int]:
    path = (derived / SAMPLES[set_name]).as_posix()
    return [r[0] for r in duckdb.execute(f"SELECT ROW_ID FROM '{path}' ORDER BY ROW_ID").fetchall()]


def load_notes(row_ids: list[int], derived: Path = DERIVED) -> dict[int, str]:
    path = (derived / "candidates.parquet").as_posix()
    rows = duckdb.execute(f"SELECT ROW_ID, TEXT FROM '{path}' WHERE list_contains(?, ROW_ID)",
                          [list(row_ids)]).fetchall()
    notes = {int(r): t for r, t in rows}
    missing = sorted(set(row_ids) - set(notes))
    if missing:
        raise KeyError(f"ROW_IDs not in candidates: {missing}")
    return notes
