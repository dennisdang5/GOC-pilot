"""Round comparison report on synthetic eval JSONs (no MIMIC data)."""

import pytest

from src.eval import compare_rounds as cr
from src.eval import metrics as m

ROUNDS = {
    "r0": {"date": "2026-10-29", "prompt_hash": {"zero_shot": "a" * 12, "few_shot": "b" * 12},
           "carc_job": "1", "gpu": "A100", "changes": "baseline"},
    "r1": {"date": "2026-11-09", "prompt_hash": {"zero_shot": "c" * 12, "few_shot": "d" * 12},
           "carc_job": None, "gpu": "A100", "changes": "stricter rules"},
}
ROW_IDS = list(range(1, 21))  # gold yes: 1-5, no: 6-20


def fake_eval(fps: list[int], fns: list[int], fingerprint="g") -> dict:
    tp, fn = 5 - len(fns), len(fns)
    fp, tn = len(fps), 15 - len(fps)
    s = m.scores({"tp": tp, "fp": fp, "fn": fn, "tn": tn})
    cfg = {"primary": s, "strict": s, "spans": {"yes": {"spans": tp + fp, "verified": tp},
                                               "no": {"spans": 0, "verified": 0}},
           "false_positives": fps, "false_negatives": fns}
    return {"set": "dev", "n": 20, "row_ids": ROW_IDS, "gold_fingerprint": fingerprint,
            "configs": {"m_zero_shot": cfg}}


def test_fewer_false_positives_is_better_when_significant():
    r0 = fake_eval(fps=list(range(6, 18)), fns=[])   # 12 FP
    r1 = fake_eval(fps=[6], fns=[])                  # 1 FP: 11 notes fixed, none broken
    (t,) = cr.step_tests(r0, r1)
    assert (t["only_prev"], t["only_new"]) == (0, 11)
    assert cr.verdict(t) == "better"


def test_small_change_is_comparable_and_worse_is_detected():
    r0 = fake_eval(fps=[6, 7], fns=[])
    r1 = fake_eval(fps=[6], fns=[1])                 # one fixed, one broken
    (t,) = cr.step_tests(r0, r1)
    assert (t["only_prev"], t["only_new"]) == (1, 1) and cr.verdict(t) == "comparable"
    (t,) = cr.step_tests(fake_eval([], []), fake_eval(list(range(6, 18)), []))
    assert cr.verdict(t) == "worse"


def test_render_lists_rounds_deltas_and_tests():
    scored = {"r0": fake_eval(list(range(6, 18)), []), "r1": fake_eval([6], [1])}
    md = cr.render(ROUNDS, scored)
    assert "| **r0** | 2026-10-29 | 1 (A100)" in md and "stricter rules" in md
    assert "r0 → r1" in md and "| -11 | +1 |" in md
    assert "better" in md
    assert "Δ F1" in md


def test_render_single_round_and_unscored():
    md = cr.render(ROUNDS, {"r0": fake_eval([6], [])})
    assert "**r1** (not scored yet)" in md and "nothing to compare yet" in md


def test_different_gold_refused():
    with pytest.raises(ValueError, match="different notes or gold labels"):
        cr.check_comparable({"r0": fake_eval([], []), "r1": fake_eval([], [], fingerprint="h")})
