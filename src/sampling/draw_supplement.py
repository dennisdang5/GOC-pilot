"""Draw the enriched test supplement test_b -> data/derived/test_b_sample.parquet.

Run from anywhere:  python -m src.sampling.draw_supplement

Design (approved 2026-10-26): the physician labeled 9/50 yes on the original test set, too few
positives to estimate sensitivity. test_b adds 50 notes from the 'strong' stratum
(src/sampling/strong.py) for the physician. The original test and dev samples are untouched.
- Per-category quotas: Physician 32, Discharge summary 6, General 6, Social Work 6.
- Excludes every patient already in test or dev; at most 1 note per patient.
- New seed. stratum = 'strong'. Reported separately from the original test set.

Refuses to overwrite an existing sample. Prints counts only.
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from src.sampling.draw import COLUMNS, draw_set
from src.sampling.strong import END_TIME_SQL, is_strong

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
STRATA = (DERIVED / "strata.parquet").as_posix()
CANDIDATES = (DERIVED / "candidates.parquet").as_posix()
ADMISSIONS = (ROOT / "data" / "parquet" / "admissions.parquet").as_posix()
EXISTING = [DERIVED / "test_sample.parquet", DERIVED / "dev_sample.parquet"]
OUT = DERIVED / "test_b_sample.parquet"
SEED = 20261026

QUOTAS = {
    ("strong", "Physician "): 32,
    ("strong", "Discharge summary"): 6,
    ("strong", "General"): 6,
    ("strong", "Social Work"): 6,
}


def strong_pool(notes: pd.DataFrame, used_patients: set[int]) -> pd.DataFrame:
    """Strong notes from patients not yet sampled, with stratum set to 'strong'."""
    keep = pd.Series([is_strong(c, d) for c, d in zip(notes["cues"], notes["days_to_end"])],
                     index=notes.index, dtype=bool)
    pool = notes[keep & ~notes["SUBJECT_ID"].isin(used_patients)].copy()
    pool["stratum"] = "strong"
    return pool


def main() -> int:
    if OUT.exists():
        print(f"draw_supplement: refusing to overwrite {OUT.relative_to(ROOT).as_posix()} "
              "(test_b is frozen; delete by hand to redraw)")
        return 1
    try:
        notes = duckdb.sql(f"""
            SELECT s.ROW_ID, s.SUBJECT_ID, s.HADM_ID, s.CATEGORY, s.n_chars, s.cues,
                   date_diff('day', c.CHARTDATE, ({END_TIME_SQL})::DATE) AS days_to_end
            FROM '{STRATA}' s
            JOIN (SELECT ROW_ID, CHARTDATE FROM '{CANDIDATES}') c USING (ROW_ID)
            JOIN '{ADMISSIONS}' a ON a.HADM_ID = s.HADM_ID
            ORDER BY s.ROW_ID
        """).df()
    except Exception as e:
        print(f"draw_supplement: FAILED reading strata/candidates/admissions ({type(e).__name__})")
        return 1

    used = set(pd.concat([pd.read_parquet(p)["SUBJECT_ID"] for p in EXISTING]))
    pool = strong_pool(notes, used)
    print(f"strong pool after excluding {len(used)} sampled patients: {len(pool):,} notes, "
          f"{pool['SUBJECT_ID'].nunique():,} patients")

    test_b = draw_set(pool, QUOTAS, np.random.default_rng(SEED))
    assert not set(test_b["SUBJECT_ID"]) & used, "test_b shares a patient with test/dev"
    assert test_b["SUBJECT_ID"].is_unique, "test_b: a patient appears twice"
    assert len(test_b) == sum(QUOTAS.values()), f"test_b: wrong size {len(test_b)}"
    assert list(test_b.columns) == COLUMNS

    test_b.to_parquet(OUT, index=False)
    print(f"test_b: {len(test_b)} notes, {test_b['SUBJECT_ID'].nunique()} patients, "
          f"{test_b['HADM_ID'].nunique()} admissions -> {OUT.relative_to(ROOT).as_posix()}")
    for cat, n in test_b.groupby("CATEGORY").size().items():
        print(f"  {cat!r:<22}{n:>4}")
    print(f"\nseed {SEED}; patient overlap with test/dev: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
