"""Draw the test and dev samples from data/derived/strata.parquet.

Run from anywhere:  python -m src.sampling.draw

Design (approved 2026-10-16):
- Test 35 cues_present + 15 cues_missing; dev 21 + 9.
- cues_present uses per-category quotas (Consult skipped, too rare); cues_missing is simple random.
- At most 1 note per patient across test + dev combined. Test is drawn first, then its patients
  are removed before drawing dev.
- No length filter. Fixed seed. No sampling weights (removed 2026-10-16): results are reported
  on the sample, unweighted, with per-stratum breakdowns.
- label_order = random 1..n display order, so labeling is shuffled with the stratum hidden.

Refuses to overwrite an existing sample: the test set is frozen once drawn. Prints counts only.
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
STRATA = (ROOT / "data" / "derived" / "strata.parquet").as_posix()
OUT = {
    "test": ROOT / "data" / "derived" / "test_sample.parquet",
    "dev": ROOT / "data" / "derived" / "dev_sample.parquet",
}
SEED = 20261016

# (stratum, category or None for all categories) -> n. Exact CATEGORY literals.
QUOTAS = {
    "test": {
        ("cues_present", "Physician "): 25,
        ("cues_present", "Discharge summary"): 4,
        ("cues_present", "General"): 3,
        ("cues_present", "Social Work"): 3,
        ("cues_missing", None): 15,
    },
    "dev": {
        ("cues_present", "Physician "): 15,
        ("cues_present", "Discharge summary"): 2,
        ("cues_present", "General"): 2,
        ("cues_present", "Social Work"): 2,
        ("cues_missing", None): 9,
    },
}
COLUMNS = ["ROW_ID", "SUBJECT_ID", "HADM_ID", "CATEGORY", "stratum", "n_chars", "label_order"]


def draw_set(pool: pd.DataFrame, quotas: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Draw one set; each cell excludes patients already used in this or earlier sets."""
    used: set[int] = set()
    parts = []
    for (stratum, category), n in quotas.items():
        cell = pool[pool["stratum"] == stratum]
        if category is not None:
            cell = cell[cell["CATEGORY"] == category]
        cell = cell[~cell["SUBJECT_ID"].isin(used)]
        # one random note per patient, then n random patients
        cell = cell.sample(frac=1, random_state=rng).drop_duplicates("SUBJECT_ID")
        if len(cell) < n:
            raise RuntimeError(f"cell {stratum}/{category!r}: {len(cell)} patients < quota {n}")
        picked = cell.head(n).copy()
        used.update(picked["SUBJECT_ID"])
        parts.append(picked)
    out = pd.concat(parts, ignore_index=True)
    out["label_order"] = rng.permutation(len(out)) + 1
    return out[COLUMNS].sort_values("label_order", ignore_index=True)


def main() -> int:
    existing = [p.relative_to(ROOT).as_posix() for p in OUT.values() if p.exists()]
    if existing:
        print(f"draw: refusing to overwrite {existing} (test set is frozen; delete by hand to redraw)")
        return 1
    try:
        pool = duckdb.sql(
            f"SELECT ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, stratum, n_chars FROM '{STRATA}'"
            " ORDER BY ROW_ID"
        ).df()
    except Exception as e:
        print(f"draw: FAILED reading strata ({type(e).__name__})")
        return 1

    rng = np.random.default_rng(SEED)
    test = draw_set(pool, QUOTAS["test"], rng)
    dev = draw_set(pool[~pool["SUBJECT_ID"].isin(test["SUBJECT_ID"])], QUOTAS["dev"], rng)

    overlap = set(test["SUBJECT_ID"]) & set(dev["SUBJECT_ID"])
    assert not overlap, f"{len(overlap)} patients in both test and dev"
    for name, df in (("test", test), ("dev", dev)):
        assert df["SUBJECT_ID"].is_unique, f"{name}: a patient appears twice"
        assert len(df) == sum(QUOTAS[name].values()), f"{name}: wrong size {len(df)}"

    for name, df in (("test", test), ("dev", dev)):
        df.to_parquet(OUT[name], index=False)
        print(f"{name}: {len(df)} notes, {df['SUBJECT_ID'].nunique()} patients, "
              f"{df['HADM_ID'].nunique()} admissions -> {OUT[name].relative_to(ROOT).as_posix()}")
        tab = df.groupby(["stratum", "CATEGORY"]).size()
        for (stratum, cat), n in tab.sort_index(ascending=[False, True]).items():
            print(f"  {stratum:<14}{cat!r:<22}{n:>4}")
    print(f"\nseed {SEED}; patient overlap test/dev: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
