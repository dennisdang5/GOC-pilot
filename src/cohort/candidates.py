"""Pull candidate notes for the cohort -> data/derived/candidates.parquet.

Run from anywhere:  python -m src.cohort.candidates

Candidates = non-error notes in the kept categories, linked to a cohort admission,
with empty/whitespace-only notes dropped and exact duplicate text within an admission
removed (lowest ROW_ID kept). TEXT is stored unmodified. Prints counts only.
"""

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
NOTES = (ROOT / "data" / "parquet" / "noteevents.parquet").as_posix()
COHORT = (ROOT / "data" / "derived" / "cohort.parquet").as_posix()
OUT = ROOT / "data" / "derived" / "candidates.parquet"

# Exact literals from reports/profile.json -- trailing spaces matter.
# 'Nursing' and 'Case Management ' excluded from candidates (decided 2026-10-15); the cohort
# still requires a 'Nursing' note as a documentation-period marker (src/cohort/build.py).
KEPT_CATEGORIES = [
    "Physician ",
    "General",
    "Social Work",
    "Consult",
    "Discharge summary",
]


def main() -> int:
    con = duckdb.connect()
    cats = ", ".join(f"'{c}'" for c in KEPT_CATEGORIES)
    try:
        con.execute(f"""
            CREATE TEMP TABLE notes AS
            SELECT n.ROW_ID, n.SUBJECT_ID, n.HADM_ID, n.CATEGORY, n.DESCRIPTION,
                   n.CHARTDATE, n.CHARTTIME, n.TEXT,
                   n.TEXT IS NULL OR trim(n.TEXT) = '' AS is_empty
            FROM '{NOTES}' n
            JOIN '{COHORT}' c USING (HADM_ID)
            WHERE COALESCE(n.ISERROR, 0) = 0 AND n.CATEGORY IN ({cats})
        """)
        con.execute("""
            CREATE TEMP TABLE ranked AS
            SELECT *,
                   row_number() OVER (PARTITION BY HADM_ID, md5(TEXT) ORDER BY ROW_ID) > 1
                       AS is_dup
            FROM notes WHERE NOT is_empty
        """)
        counts = con.execute("""
            SELECT n.CATEGORY,
                   count(*),
                   count(*) FILTER (WHERE n.is_empty),
                   (SELECT count(*) FROM ranked r WHERE r.CATEGORY = n.CATEGORY AND r.is_dup),
                   (SELECT count(*) FROM ranked r WHERE r.CATEGORY = n.CATEGORY AND NOT r.is_dup)
            FROM notes n GROUP BY n.CATEGORY ORDER BY 5 DESC
        """).fetchall()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"""
            COPY (
                SELECT ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, DESCRIPTION,
                       CHARTDATE, CHARTTIME, length(TEXT) AS n_chars, TEXT
                FROM ranked WHERE NOT is_dup ORDER BY ROW_ID
            ) TO '{OUT.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """)
        n_out, n_adm = con.execute(
            f"SELECT count(*), count(DISTINCT HADM_ID) FROM '{OUT.as_posix()}'"
        ).fetchone()
    except Exception as e:
        print(f"candidates: FAILED ({type(e).__name__})")
        return 1

    print(f"{'category':<22}{'in cohort':>11}{'empty':>8}{'exact dup':>11}{'kept':>10}")
    tot = [0, 0, 0, 0]
    for cat, n, empty, dup, kept in counts:
        print(f"{cat!r:<22}{n:>11,}{empty:>8,}{dup:>11,}{kept:>10,}")
        tot = [t + x for t, x in zip(tot, (n, empty, dup, kept))]
    print(f"{'TOTAL':<22}{tot[0]:>11,}{tot[1]:>8,}{tot[2]:>11,}{tot[3]:>10,}")
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}: {n_out:,} notes, {n_adm:,} admissions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
