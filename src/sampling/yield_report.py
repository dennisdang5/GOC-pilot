"""Which screening signals actually yield GOC 'yes' labels -> reports/yield_report.json.

Run from anywhere:  python -m src.sampling.yield_report [LABELS_DIR]

LABELS_DIR defaults to data/labels/; pass ../GOC-labeler/labels after a git pull.

Used to design the enriched test supplement (test_b, approved 2026-10-26). For each candidate
signal it reports the pool size and the yes / no / unclear counts among labeled dev and test
notes. The user approved looking at test-label aggregates for this sampling design only; the
regex is never a method under evaluation. Regexes run inside DuckDB; no note text and no
ROW_IDs are printed. Prints counts only.
"""

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

from src.labeling.collect import LABEL_DIR, read_labels
from src.sampling.cues import CUE_PATTERNS, PROBE_PATTERNS
from src.sampling.strong import END_TIME_SQL, FAMILIES

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = (ROOT / "data" / "derived" / "candidates.parquet").as_posix()
STRATA = (ROOT / "data" / "derived" / "strata.parquet").as_posix()
ADMISSIONS = (ROOT / "data" / "parquet" / "admissions.parquet").as_posix()
OUT = ROOT / "reports" / "yield_report.json"

PROBES = ["probe_family_meeting_nonheading", "probe_goc_nonheading",
          "probe_family_meeting_heading", "probe_goc_heading"]

# Days from note CHARTDATE to the end event (in-hospital death, else hospice discharge).
TIMING = """CASE WHEN end_time IS NULL THEN 'no death/hospice dc'
                 WHEN days_to_end <= 2 THEN '0-2 d'
                 WHEN days_to_end <= 7 THEN '3-7 d'
                 ELSE '>7 d' END"""

# Candidate signals for the strong stratum: name -> SQL boolean over table f.
SIGNALS = {
    "any cue (cues_present)": "n_cues > 0",
    "FM/GOC non-heading": "probe_family_meeting_nonheading OR probe_goc_nonheading",
    "discussion-type cue": "discussed_code_status OR withdraw_care OR end_of_life"
                           " OR health_care_proxy",
    ">=2 cue families": "n_families >= 2",
    ">=3 cue families": "n_families >= 3",
    "Social Work + any cue": "CATEGORY = 'Social Work' AND n_cues > 0",
    "timing <=7 d": "days_to_end <= 7",
    "timing <=2 d": "days_to_end <= 2",
}
STRONG = "(" + ") OR (".join([SIGNALS["FM/GOC non-heading"], SIGNALS["discussion-type cue"],
                              SIGNALS[">=2 cue families"], SIGNALS["Social Work + any cue"]]) + ")"
SIGNALS["strong (any of 4)"] = STRONG
SIGNALS["strong AND timing <=7 d"] = f"({STRONG}) AND days_to_end <= 7"
SIGNALS["strong AND timing <=2 d"] = f"({STRONG}) AND days_to_end <= 2"
SIGNALS[">=2 families AND timing <=7 d"] = "n_families >= 2 AND days_to_end <= 7"


def load_labels(label_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(label_dir.glob("*.jsonl")):
        latest, _ = read_labels(path)
        for lab in latest.values():
            rows.append({"row_id": lab.row_id,
                         "lset": "test" if lab.assignment.startswith("test") else "dev",
                         "label": lab.goc_present})
    return pd.DataFrame(rows, columns=["row_id", "lset", "label"])


def counts(con, where: str, group: str | None = None) -> list[dict]:
    """Pool n plus yes/no/unclear per labeled set, optionally grouped by a SQL expression."""
    g = group or "'all'"
    q = f"""
        SELECT {g} AS grp, count(*) AS pool,
               count(*) FILTER (WHERE lset = 'test') AS test_n,
               count(*) FILTER (WHERE lset = 'test' AND label = 'yes') AS test_yes,
               count(*) FILTER (WHERE lset = 'test' AND label = 'unclear') AS test_unclear,
               count(*) FILTER (WHERE lset = 'dev') AS dev_n,
               count(*) FILTER (WHERE lset = 'dev' AND label = 'yes') AS dev_yes,
               count(*) FILTER (WHERE lset = 'dev' AND label = 'unclear') AS dev_unclear
        FROM f WHERE {where} GROUP BY 1 ORDER BY 1
    """
    cols = ["grp", "pool", "test_n", "test_yes", "test_unclear", "dev_n", "dev_yes", "dev_unclear"]
    return [dict(zip(cols, r)) for r in con.execute(q).fetchall()]


def main() -> int:
    label_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else LABEL_DIR
    labels = load_labels(label_dir)
    if labels.empty:
        print(f"yield_report: no labels in {label_dir.as_posix()}/")
        return 1

    patterns = {**CUE_PATTERNS, **{p: PROBE_PATTERNS[p] for p in PROBES}}
    names = list(patterns)
    params = {f"p{i}": patterns[n] for i, n in enumerate(names)}
    flags = ",\n".join(f"regexp_matches(c.TEXT, $p{i}, 'i') AS {n}" for i, n in enumerate(names))
    fam = " + ".join(f"({' OR '.join(cs)})::INT" for cs in FAMILIES.values())
    n_cues = " + ".join(f"{c}::INT" for c in CUE_PATTERNS)

    con = duckdb.connect()
    con.register("labels", labels)
    try:
        con.execute(f"""
            CREATE TEMP TABLE m AS
            SELECT c.ROW_ID, c.SUBJECT_ID, c.CATEGORY, c.CHARTDATE, s.stratum,
                   {END_TIME_SQL} AS end_time,
                   {flags}
            FROM '{CANDIDATES}' c
            JOIN '{STRATA}' s USING (ROW_ID)
            JOIN '{ADMISSIONS}' a ON a.HADM_ID = c.HADM_ID
        """, params)
        con.execute(f"""
            CREATE TEMP TABLE f AS
            SELECT m.*, ({n_cues}) AS n_cues, ({fam}) AS n_families,
                   date_diff('day', CHARTDATE, end_time::DATE) AS days_to_end,
                   l.lset, l.label
            FROM m LEFT JOIN labels l ON l.row_id = m.ROW_ID
        """)
        n_missing = con.execute(
            "SELECT count(*) FROM labels WHERE row_id NOT IN (SELECT ROW_ID FROM f)").fetchone()[0]
        report = {
            "labels_not_in_pool": n_missing,
            "by_stratum_category": counts(con, "TRUE", "stratum || ' / ' || trim(CATEGORY)"),
            "by_cue": {n: counts(con, n)[0] if counts(con, n) else None for n in CUE_PATTERNS},
            "by_probe": {p: counts(con, p)[0] if counts(con, p) else None for p in PROBES},
            "by_n_families": counts(con, "TRUE", "least(n_families, 3)::VARCHAR"),
            "by_timing": counts(con, "TRUE", TIMING),
            "signals": {k: (counts(con, w) or [None])[0] for k, w in SIGNALS.items()},
            "strong_and_timing7_by_category": counts(
                con, SIGNALS["strong AND timing <=7 d"], "trim(CATEGORY)"),
            "strong_by_category": counts(con, STRONG, "trim(CATEGORY)"),
            "fam2_and_timing7_by_category": counts(
                con, SIGNALS[">=2 families AND timing <=7 d"], "trim(CATEGORY)"),
            "fam3_by_category": counts(con, SIGNALS[">=3 cue families"], "trim(CATEGORY)"),
        }
    except Exception as e:
        print(f"yield_report: FAILED ({type(e).__name__})")
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, default=int))

    def line(name, r):
        if r is None:
            return f"{name:<34}{'—':>8}"
        return (f"{name:<34}{r['pool']:>8,}   test {r['test_yes']:>2}/{r['test_n']:<3}"
                f"(unc {r['test_unclear']})   dev {r['dev_yes']:>2}/{r['dev_n']:<3}"
                f"(unc {r['dev_unclear']})")

    print(f"labels: {len(labels)} ({labels['lset'].value_counts().to_dict()}); "
          f"not in pool: {n_missing}")
    print(f"\n{'group':<34}{'pool':>8}   yes/n per labeled set")
    for title, key in (("stratum / category", "by_stratum_category"),
                       ("cue families (3 = 3+)", "by_n_families"),
                       ("timing to death / hospice dc", "by_timing"),
                       ("strong by category", "strong_by_category"),
                       ("strong AND <=7 d by category", "strong_and_timing7_by_category"),
                       (">=2 families AND <=7 d by category", "fam2_and_timing7_by_category"),
                       (">=3 families by category", "fam3_by_category")):
        print(f"\n-- {title}")
        for r in report[key]:
            print(line(str(r["grp"]), r))
    for title, key in (("cues", "by_cue"), ("probes", "by_probe"), ("signals", "signals")):
        print(f"\n-- {title}")
        for n, r in report[key].items():
            print(line(n, r))
    print(f"\nwrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
