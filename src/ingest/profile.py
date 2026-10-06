"""Profile the Parquet tables -> reports/profile.json (counts only).

Run from anywhere:  python -m src.ingest.profile

Category and discharge-location strings are stored with repr() so stray whitespace
and case differences are visible; the cohort query is written from these literals.
"""

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "data" / "parquet"
OUT = ROOT / "reports" / "profile.json"

NOTES = (PARQUET / "noteevents.parquet").as_posix()
ADMISSIONS = (PARQUET / "admissions.parquet").as_posix()
DIAGNOSES = (PARQUET / "diagnoses_icd.parquet").as_posix()

QUERIES = {
    "category_counts": f"""
        SELECT CATEGORY,
               count(*) AS n_all,
               count(*) FILTER (WHERE COALESCE(ISERROR, 0) = 0) AS n_iserror_excluded
        FROM '{NOTES}'
        GROUP BY CATEGORY
        ORDER BY n_all DESC
    """,
    "discharge_location_counts": f"""
        SELECT DISCHARGE_LOCATION, count(*) AS n
        FROM '{ADMISSIONS}'
        GROUP BY DISCHARGE_LOCATION
        ORDER BY n DESC
    """,
    "v667_distinct_hadm": f"""
        SELECT count(DISTINCT HADM_ID) FROM '{DIAGNOSES}' WHERE ICD9_CODE = 'V667'
    """,
    "admissions_with_deathtime": f"""
        SELECT count(*) FROM '{ADMISSIONS}' WHERE DEATHTIME IS NOT NULL
    """,
    "iserror_counts": f"""
        SELECT ISERROR, count(*) AS n
        FROM '{NOTES}'
        GROUP BY ISERROR
        ORDER BY ISERROR NULLS FIRST
    """,
}


def run(con: duckdb.DuckDBPyConnection, name: str, sql: str):
    rows = con.execute(sql).fetchall()
    if name == "category_counts":
        return [{"category": repr(c), "n_all": a, "n_iserror_excluded": b} for c, a, b in rows]
    if name == "discharge_location_counts":
        return [{"discharge_location": repr(d), "n": n} for d, n in rows]
    if name == "iserror_counts":
        return [{"iserror": v, "n": n} for v, n in rows]
    return rows[0][0]


def main() -> int:
    con = duckdb.connect()
    profile = {}
    failed = False
    for name, sql in QUERIES.items():
        try:
            profile[name] = run(con, name, sql)
        except Exception as e:
            print(f"{name}: FAILED ({type(e).__name__})")
            failed = True
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
