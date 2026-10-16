"""How often each screening cue matches the candidate pool -> reports/cue_frequency.json.

Run from anywhere:  python -m src.sampling.cue_frequency

Used to spot template phrases that match nearly every note before the cue list is frozen.
Prints counts only.
"""

import json
import sys
from pathlib import Path

import duckdb

from src.sampling.cues import CUE_PATTERNS, PROBE_PATTERNS

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = (ROOT / "data" / "derived" / "candidates.parquet").as_posix()
OUT = ROOT / "reports" / "cue_frequency.json"


def main() -> int:
    patterns = {**CUE_PATTERNS, **PROBE_PATTERNS}
    names = list(patterns)
    cue_cols = [n for n in names if n in CUE_PATTERNS]
    con = duckdb.connect()
    try:
        flags = ",\n".join(
            f"regexp_matches(TEXT, $p{i}, 'i') AS {n}" for i, n in enumerate(names)
        )
        params = {f"p{i}": patterns[n] for i, n in enumerate(names)}
        con.execute(
            f"CREATE TEMP TABLE m AS SELECT ROW_ID, CATEGORY, {flags} FROM '{CANDIDATES}'",
            params,
        )
        any_cue = " OR ".join(cue_cols)
        any_all = " OR ".join(names)
        n_cue = " + ".join(f"{c}::INT" for c in cue_cols)
        con.execute(f"""
            CREATE TEMP TABLE m2 AS
            SELECT *, ({any_cue}) AS any_cue, ({any_all}) AS any_with_probes,
                   ({n_cue}) AS n_cues
            FROM m
        """)
        total = con.execute("SELECT count(*) FROM m2").fetchone()[0]
        cats = [r[0] for r in con.execute(
            "SELECT CATEGORY FROM m2 GROUP BY 1 ORDER BY count(*) DESC").fetchall()]
        cat_n = dict(con.execute("SELECT CATEGORY, count(*) FROM m2 GROUP BY 1").fetchall())

        rows = {}
        for n in names:
            hit, only = con.execute(
                f"SELECT count(*) FILTER (WHERE {n}), "
                f"count(*) FILTER (WHERE {n} AND n_cues = 1) FROM m2"
            ).fetchone()
            by_cat = dict(con.execute(
                f"SELECT CATEGORY, count(*) FILTER (WHERE {n}) FROM m2 GROUP BY 1"
            ).fetchall())
            rows[n] = {
                "pattern": patterns[n],
                "probe_only": n in PROBE_PATTERNS,
                "notes": hit,
                "pct_pool": round(100 * hit / total, 2),
                "only_cue": only if n in CUE_PATTERNS else None,
                "by_category": {c: by_cat.get(c, 0) for c in cats},
            }
        overall = {}
        for col in ("any_cue", "any_with_probes"):
            by_cat = dict(con.execute(
                f"SELECT CATEGORY, count(*) FILTER (WHERE {col}) FROM m2 GROUP BY 1"
            ).fetchall())
            hit = sum(by_cat.values())
            overall[col] = {
                "notes": hit,
                "pct_pool": round(100 * hit / total, 2),
                "pct_by_category": {c: round(100 * by_cat.get(c, 0) / cat_n[c], 1) for c in cats},
            }
    except Exception as e:
        print(f"cue_frequency: FAILED ({type(e).__name__})")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"total_notes": total, "category_notes": cat_n,
                               "phrases": rows, "overall": overall}, indent=2))

    short = {"Physician ": "Phys", "General": "Gen", "Discharge summary": "DS",
             "Social Work": "SW", "Consult": "Cons"}
    head = "".join(f"{short.get(c, c[:5]):>8}" for c in cats)
    print(f"pool: {total:,} notes\n")
    print(f"{'phrase':<24}{'notes':>8}{'%pool':>7}{'only':>7}{head}")
    for n, r in rows.items():
        only = "" if r["only_cue"] is None else f"{r['only_cue']:,}"
        cells = "".join(f"{r['by_category'][c]:>8,}" for c in cats)
        print(f"{n:<24}{r['notes']:>8,}{r['pct_pool']:>7}{only:>7}{cells}")
    print()
    for col, o in overall.items():
        cells = "".join(f"{o['pct_by_category'][c]:>7}%" for c in cats)
        print(f"{col:<24}{o['notes']:>8,}{o['pct_pool']:>7}{'':>7}{cells}")
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
