"""Markdown rendering of an eval report (synthetic numbers only)."""

from src.eval.report_md import render


def _p(k, n):
    return None if n == 0 else {"k": k, "n": n, "est": k / n, "lo": 0.1, "hi": 0.9}


def _m(tp, fp, fn, tn, f1, few=None):
    m = {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "n": tp + fp + fn + tn, "positives": tp + fn,
         "sensitivity": _p(tp, tp + fn), "ppv": _p(tp, tp + fp),
         "specificity": _p(tn, tn + fp), "f1": f1}
    if few is not None:
        m["few_positives"] = few
    return m


def _cfg(m, fps, fns):
    return {"primary": m, "exclude_unclear": m, "strict": m,
            "by_stratum": {"cues_present": {**m, "few_positives": False},
                           "cues_missing": _m(0, 0, 1, 2, None, few=True)},
            "by_part": None, "failures": {"n": 0, "by_type": {}},
            "spans": {"yes": {"spans": 3, "verified": 2}, "no": {"spans": 0, "verified": 0}},
            "false_positives": fps, "false_negatives": fns}


REPORT = {
    "set": "dev", "n": 6, "gold": {"yes": 2, "no": 4}, "gold_by_stratum": {
        "cues_present": {"yes": 1, "no": 2}, "cues_missing": {"yes": 1, "no": 2}},
    "configs": {
        "weak_zero_shot": _cfg(_m(0, 0, 2, 4, None), [], [987654, 876543]),
        "good_few_shot": _cfg(_m(2, 1, 0, 3, 0.8), [765432], []),
    },
    "mcnemar": {"exploratory": True, "pairs": [
        {"a": "good_few_shot", "b": "weak_zero_shot", "only_a_correct": 2,
         "only_b_correct": 1, "p": 1.0, "p_holm": 1.0}]},
}


def test_main_table_sorted_by_f1_with_na():
    md = render(REPORT)
    good, weak = md.index("| `good_few_shot` | 2 / 1 / 0 / 3"), md.index("| `weak_zero_shot` |")
    assert good < weak
    weak_row = md[weak:md.index("\n", weak)]
    assert "| NA |" in weak_row  # PPV undefined and F1 undefined


def test_sections_and_flags():
    md = render(REPORT)
    for heading in ("## Main results", "## By stratum", "## Sensitivity analyses",
                    "## Evidence spans", "## Model comparisons", "## How to read this"):
        assert heading in md
    assert "comparable" in md
    assert "## By part" not in md


def test_dev_strata_compact_one_row_per_config():
    md = render(REPORT)
    sec = md[md.index("## By stratum"):md.index("## Sensitivity analyses")]
    rows = [ln for ln in sec.splitlines() if ln.startswith("| `")]
    assert len(rows) == 2
    good = next(ln for ln in rows if "good_few_shot" in ln)
    assert "2 / 1 / 0 / 3" in good and "0 / 0 / 1 / 2" in good  # both strata on one row
    assert "`cues_missing` has fewer than 5" in sec


def test_test_set_keeps_full_strata_table():
    md = render({**REPORT, "set": "test_a"})
    sec = md[md.index("## By stratum"):md.index("## Sensitivity analyses")]
    assert "`cues_missing` *" in sec
    assert "| config | group |" in sec


def test_no_row_ids():
    md = render(REPORT)
    for rid in ("987654", "876543", "765432"):
        assert rid not in md
