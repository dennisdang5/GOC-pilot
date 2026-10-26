"""The 'strong' sampling stratum for the enriched test supplement (test_b).

A sampling tool only -- never a method under evaluation; src/eval/ must not import it.

Rule (approved 2026-10-26 from reports/yield_report.json): a note is strong if its matched cues
(strata.parquet `cues`) span >= 2 cue families AND it was charted <= 7 days before the
admission's end event (in-hospital death, else discharge to hospice). Notes in admissions with
neither event are never strong. Labeled yield on dev + test was 8/16 for this rule.
"""

import pandas as pd

from src.sampling.cues import CUE_PATTERNS

FAMILIES: dict[str, list[str]] = {
    "discussion": ["family_meeting", "goals_of_care", "discussed_code_status", "end_of_life",
                   "quality_of_life"],
    "transition": ["comfort_care", "hospice", "palliative", "withdraw_care", "redirect_care"],
    "surrogate": ["health_care_proxy", "advance_directive", "molst_polst"],
    "values": ["important_to", "matters_most", "hopes_to", "wants_to_be_able_to",
               "would_not_want", "wishes"],
}
assert sorted(sum(FAMILIES.values(), [])) == sorted(CUE_PATTERNS)
CUE_FAMILY = {cue: fam for fam, cues in FAMILIES.items() for cue in cues}

MIN_FAMILIES = 2
MAX_DAYS_TO_END = 7

# SQL for the admission end event; table alias `a` = admissions.
END_TIME_SQL = """CASE WHEN a.DEATHTIME IS NOT NULL THEN a.DEATHTIME
                       WHEN a.DISCHARGE_LOCATION ILIKE '%HOSPICE%' THEN a.DISCHTIME END"""


def n_families(cues) -> int:
    return len({CUE_FAMILY[c] for c in cues})


def is_strong(cues, days_to_end) -> bool:
    """cues: matched cue names; days_to_end: CHARTDATE -> end event in days, missing if none."""
    if pd.isna(days_to_end):
        return False
    return n_families(cues) >= MIN_FAMILIES and days_to_end <= MAX_DAYS_TO_END
