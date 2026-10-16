"""Assign each candidate note a sampling stratum -> data/derived/strata.parquet.

Run from anywhere:  python -m src.sampling.strata

stratum = 'cues_present' if the note matches any pattern in src/sampling/cues.py CUE_PATTERNS,
else 'cues_missing'. `cues` lists the matched cue names. This steers sampling only and is never
a GOC label. No note text is written to the output. Prints counts only.
"""

import sys
from pathlib import Path

import duckdb

from src.sampling.cues import CUE_PATTERNS

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = (ROOT / "data" / "derived" / "candidates.parquet").as_posix()
OUT = ROOT / "data" / "derived" / "strata.parquet"


def main() -> int:
    names = list(CUE_PATTERNS)
    params = {f"p{i}": CUE_PATTERNS[n] for i, n in enumerate(names)}
    matched = ", ".join(
        f"CASE WHEN regexp_matches(TEXT, $p{i}, 'i') THEN '{n}' END" for i, n in enumerate(names)
    )
    con = duckdb.connect()
    try:
        con.execute(f"""
            CREATE TEMP TABLE s AS
            SELECT ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, n_chars,
                   list_filter([{matched}], x -> x IS NOT NULL) AS cues
            FROM '{CANDIDATES}'
        """, params)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"""
            COPY (
                SELECT ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, n_chars,
                       CASE WHEN len(cues) > 0 THEN 'cues_present' ELSE 'cues_missing' END
                           AS stratum,
                       cues
                FROM s ORDER BY ROW_ID
            ) TO '{OUT.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """)
        counts = con.execute(f"""
            SELECT coalesce(CATEGORY, 'TOTAL'),
                   count(*) FILTER (WHERE stratum = 'cues_present'),
                   count(*) FILTER (WHERE stratum = 'cues_missing'),
                   count(*)
            FROM '{OUT.as_posix()}' GROUP BY ROLLUP (CATEGORY) ORDER BY 4 DESC
        """).fetchall()
        pts = con.execute(f"""
            SELECT stratum, count(DISTINCT HADM_ID), count(DISTINCT SUBJECT_ID)
            FROM '{OUT.as_posix()}' GROUP BY 1 ORDER BY 1 DESC
        """).fetchall()
    except Exception as e:
        print(f"strata: FAILED ({type(e).__name__})")
        return 1

    print(f"{'category':<22}{'cues_present':>14}{'cues_missing':>14}{'total':>10}")
    for cat, p, m, t in counts:
        print(f"{cat!r:<22}{p:>14,}{m:>14,}{t:>10,}")
    print()
    for stratum, n_adm, n_pt in pts:
        print(f"{stratum:<14} {n_adm:>6,} admissions {n_pt:>6,} patients")
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
