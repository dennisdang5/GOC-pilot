"""Build the admission-level cohort -> data/derived/cohort.parquet.

Run from anywhere:  python -m src.cohort.build

Cohort = admissions matching ANY inclusion reason, AND with >=1 non-error 'Nursing' note,
AND adult (>=18 complete years from DOB to ADMITTIME). See CLAUDE.md "Decisions already made".
Prints counts only.
"""

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
PARQUET = ROOT / "data" / "parquet"
OUT = ROOT / "data" / "derived" / "cohort.parquet"

NOTES = (PARQUET / "noteevents.parquet").as_posix()
ADMISSIONS = (PARQUET / "admissions.parquet").as_posix()
PATIENTS = (PARQUET / "patients.parquet").as_posix()
DIAGNOSES = (PARQUET / "diagnoses_icd.parquet").as_posix()

REASONS = ["died_in_hosp", "hospice_dc", "died_365d", "v667"]

FLAGGED = f"""
    SELECT a.SUBJECT_ID,
           a.HADM_ID,
           a.ADMITTIME,
           a.DEATHTIME IS NOT NULL                                AS died_in_hosp,
           COALESCE(a.DISCHARGE_LOCATION ILIKE '%HOSPICE%', false) AS hospice_dc,
           COALESCE(p.DOD <= a.DISCHTIME + INTERVAL 365 DAY, false) AS died_365d,
           a.HADM_ID IN (SELECT HADM_ID FROM '{DIAGNOSES}' WHERE ICD9_CODE = 'V667') AS v667,
           a.HADM_ID IN (SELECT HADM_ID FROM '{NOTES}'
                         WHERE CATEGORY = 'Nursing' AND COALESCE(ISERROR, 0) = 0
                           AND HADM_ID IS NOT NULL)                AS has_nursing,
           date_sub('year', p.DOB, a.ADMITTIME) >= 18              AS adult
    FROM '{ADMISSIONS}' a
    JOIN '{PATIENTS}' p USING (SUBJECT_ID)
"""


def main() -> int:
    con = duckdb.connect()
    try:
        con.execute(f"CREATE TEMP TABLE flagged AS {FLAGGED}")
        any_reason = " OR ".join(REASONS)
        n_all, n_incl, n_nurse, n_final = con.execute(f"""
            SELECT count(*),
                   count(*) FILTER (WHERE {any_reason}),
                   count(*) FILTER (WHERE ({any_reason}) AND has_nursing),
                   count(*) FILTER (WHERE ({any_reason}) AND has_nursing AND adult)
            FROM flagged
        """).fetchone()

        final = f"({any_reason}) AND has_nursing AND adult"
        n_single = " + ".join(f"{r}::INT" for r in REASONS)
        per_reason = con.execute(f"""
            SELECT {", ".join(f"count(*) FILTER (WHERE {r})" for r in REASONS)},
                   {", ".join(f"count(*) FILTER (WHERE {r} AND {n_single} = 1)" for r in REASONS)},
                   count(DISTINCT SUBJECT_ID)
            FROM flagged WHERE {final}
        """).fetchone()

        OUT.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"""
            COPY (SELECT SUBJECT_ID, HADM_ID, ADMITTIME, {", ".join(REASONS)}
                  FROM flagged WHERE {final} ORDER BY HADM_ID)
            TO '{OUT.as_posix()}' (FORMAT parquet)
        """)
    except Exception as e:
        print(f"cohort: FAILED ({type(e).__name__})")
        return 1

    print("Funnel (admissions):")
    print(f"  all admissions                 {n_all:>8,}")
    print(f"  any inclusion reason           {n_incl:>8,}")
    print(f"  + has 'Nursing' note           {n_nurse:>8,}")
    print(f"  + adult (final cohort)         {n_final:>8,}")
    print(f"\nFinal cohort: {per_reason[-1]:,} distinct patients")
    print(f"{'reason':<16}{'admissions':>12}{'only reason':>13}")
    k = len(REASONS)
    for i, r in enumerate(REASONS):
        print(f"{r:<16}{per_reason[i]:>12,}{per_reason[k + i]:>13,}")
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
