"""Strong stratum rule and the test_b supplement draw, on synthetic data only."""

import numpy as np
import pandas as pd
import pytest

from src.sampling import draw_supplement
from src.sampling.draw import COLUMNS, draw_set
from src.sampling.strong import is_strong, n_families


def test_families_count_distinct_families_not_cues():
    assert n_families([]) == 0
    assert n_families(["family_meeting", "goals_of_care"]) == 1  # both discussion
    assert n_families(["family_meeting", "comfort_care"]) == 2
    assert n_families(["family_meeting", "comfort_care", "wishes", "molst_polst"]) == 4


@pytest.mark.parametrize("cues, days, expected", [
    (["family_meeting", "comfort_care"], 0, True),
    (["family_meeting", "comfort_care"], 7, True),       # boundary is inclusive
    (["family_meeting", "comfort_care"], 8, False),
    (["family_meeting", "comfort_care"], -1, True),      # charted on/after the end date
    (["family_meeting", "goals_of_care"], 0, False),     # one family only
    (["family_meeting", "comfort_care"], None, False),   # no death / hospice discharge
    (["family_meeting", "comfort_care"], float("nan"), False),
    (["family_meeting", "comfort_care"], pd.NA, False),     # DuckDB nullable Int64
    ([], 0, False),
])
def test_is_strong(cues, days, expected):
    assert is_strong(cues, days) is expected


def synthetic_notes() -> pd.DataFrame:
    rows = []
    for i in range(40):
        rows.append({
            "ROW_ID": i, "SUBJECT_ID": i // 2, "HADM_ID": 1000 + i // 2,
            "CATEGORY": "Physician " if i % 4 else "Social Work", "n_chars": 100 + i,
            "cues": ["family_meeting", "hospice"] if i % 3 else ["family_meeting"],
            "days_to_end": float(i % 10) if i % 5 else float("nan"),
        })
    return pd.DataFrame(rows)


def test_strong_pool_filters_rule_and_used_patients():
    notes = synthetic_notes()
    used = {0, 1, 2}
    pool = draw_supplement.strong_pool(notes, used)
    assert len(pool) > 0
    assert not set(pool["SUBJECT_ID"]) & used
    assert (pool["stratum"] == "strong").all()
    assert all(is_strong(c, d) for c, d in zip(pool["cues"], pool["days_to_end"]))
    # every strong note from an unused patient is kept
    expected = sum(is_strong(c, d) and s not in used
                   for c, d, s in zip(notes["cues"], notes["days_to_end"], notes["SUBJECT_ID"]))
    assert len(pool) == expected


def test_draw_from_strong_pool_one_note_per_patient():
    pool = draw_supplement.strong_pool(synthetic_notes(), set())
    quotas = {("strong", "Physician "): 3, ("strong", "Social Work"): 1}
    out = draw_set(pool, quotas, np.random.default_rng(0))
    assert list(out.columns) == COLUMNS
    assert out["SUBJECT_ID"].is_unique and len(out) == 4
    assert sorted(out["label_order"]) == [1, 2, 3, 4]


def test_refuses_to_overwrite(tmp_path, monkeypatch):
    out = tmp_path / "test_b_sample.parquet"
    out.write_bytes(b"")
    monkeypatch.setattr(draw_supplement, "OUT", out)
    monkeypatch.setattr(draw_supplement, "ROOT", tmp_path)
    assert draw_supplement.main() == 1
