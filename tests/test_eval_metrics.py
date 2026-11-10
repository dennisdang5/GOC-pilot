"""Eval metrics on synthetic labels and predictions (no MIMIC data)."""

import json

import pandas as pd
import pytest

from src.eval import metrics as m
from src.llm.schema import Prediction


def pred(row_id, answer, verified=None, error=None, set_name="dev"):
    return Prediction(row_id=row_id, method="fake:1b", strategy="zero_shot", set=set_name,
                      goc_present=answer, evidence_span=None, span_verified=verified,
                      prompt_hash="x", prompt_tokens=10, truncated=error == "truncated",
                      latency_s=0.1, raw_output_path="raw", error=error)


def write_preds(pred_dir, stem, preds):
    pred_dir.mkdir(parents=True, exist_ok=True)
    (pred_dir / f"{stem}.jsonl").write_text(
        "".join(p.model_dump_json() + "\n" for p in preds), encoding="utf-8")


def write_labels(labels_dir, assignment, gold):
    labels_dir.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"row_id": r, "assignment": assignment, "goc_present": g,
                         "annotator": "ZZ", "labeled_at": "2026-10-29T00:00:00+00:00"})
             for r, g in gold.items()]
    (labels_dir / f"{assignment}_ZZ.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_wilson_known_value():
    w = m.wilson(5, 10)
    assert w["est"] == 0.5
    assert w["lo"] == pytest.approx(0.2366, abs=1e-4)
    assert w["hi"] == pytest.approx(0.7634, abs=1e-4)
    assert m.wilson(0, 0) is None


def test_scores_na_when_no_predicted_positives():
    s = m.scores({"tp": 0, "fp": 0, "fn": 3, "tn": 7})
    assert s["ppv"] is None and s["f1"] is None
    assert s["sensitivity"]["est"] == 0
    assert s["specificity"]["est"] == 1


@pytest.fixture
def dev_setup(tmp_path):
    """6 dev notes: gold yes 1,2 · unclear 3 · no 4,5,6. Strata a (1-3) / b (4-6)."""
    derived, labels, preds = tmp_path / "derived", tmp_path / "labels", tmp_path / "pred"
    derived.mkdir()
    pd.DataFrame({"ROW_ID": [1, 2, 3, 4, 5, 6], "stratum": list("aaabbb")}).to_parquet(
        derived / "dev_sample.parquet")
    write_labels(labels, "dev_A", {1: "yes", 2: "yes", 3: "unclear"})
    write_labels(labels, "dev_B", {4: "no", 5: "no", 6: "no"})
    write_labels(labels, "test_physician", {99: "yes"})  # must not be read for dev
    # good: yes on 1 (verified) and 2 (unverified), no elsewhere; 6 failed -> counts as no
    write_preds(preds, "good_zero_shot_dev",
                [pred(1, "yes", True), pred(2, "yes", False), pred(3, "no"), pred(4, "no"),
                 pred(5, "no"), pred(6, None, error="truncated")])
    # noisy: misses 2, false positive on 3 (gold unclear) and 4
    write_preds(preds, "noisy_zero_shot_dev",
                [pred(1, "yes", True), pred(2, "no"), pred(3, "yes", True), pred(4, "yes"),
                 pred(5, "no"), pred(6, "no")])
    return derived, labels, preds


def test_evaluate_rules(dev_setup):
    derived, labels, preds = dev_setup
    df = m.build_frame("dev", labels, preds, derived)
    assert 99 not in set(df["row_id"])
    r = m.evaluate("dev", df, None)
    good, noisy = r["configs"]["good_zero_shot"], r["configs"]["noisy_zero_shot"]

    assert (good["primary"]["tp"], good["primary"]["fp"], good["primary"]["fn"],
            good["primary"]["tn"]) == (2, 0, 0, 4)
    assert good["failures"] == {"n": 1, "by_type": {"truncated": [6]}}
    # strict: unverified yes on 2 becomes no
    assert (good["strict"]["tp"], good["strict"]["fn"]) == (1, 1)
    assert good["spans"] == {"yes": {"spans": 2, "verified": 1}, "no": {"spans": 0, "verified": 0}}

    # unclear counts as no in primary; excluded in exclude_unclear
    assert noisy["primary"]["fp"] == 2 and noisy["exclude_unclear"]["fp"] == 1
    assert noisy["exclude_unclear"]["n"] == 5
    assert noisy["false_positives"] == [3, 4] and noisy["false_negatives"] == [2]
    assert noisy["by_stratum"]["a"]["few_positives"] is True

    (pair,) = r["mcnemar"]["pairs"]
    assert (pair["only_a_correct"], pair["only_b_correct"]) == (3, 0)
    assert r["mcnemar"]["exploratory"] is True


def test_missing_prediction_is_an_error(dev_setup):
    derived, labels, preds = dev_setup
    write_preds(preds, "short_zero_shot_dev", [pred(1, "yes")])
    with pytest.raises(ValueError, match="short_zero_shot dev: 5 notes"):
        m.build_frame("dev", labels, preds, derived)


def test_missing_gold_is_an_error(dev_setup):
    derived, labels, preds = dev_setup
    (labels / "dev_B_ZZ.jsonl").unlink()
    with pytest.raises(ValueError, match="3 notes have no gold label"):
        m.build_frame("dev", labels, preds, derived)


def test_test_pairs_only_when_named(dev_setup):
    derived, labels, preds = dev_setup
    df = m.build_frame("dev", labels, preds, derived)
    assert m.evaluate("test_a", df, None)["mcnemar"]["pairs"] == []
    with pytest.raises(ValueError, match="unknown configs"):
        m.evaluate("test_a", df, [("good_zero_shot", "nope")])


def test_write_outputs(dev_setup, tmp_path):
    derived, labels, preds = dev_setup
    r = m.evaluate("dev", m.build_frame("dev", labels, preds, derived), None)
    m.write_outputs(r, tmp_path / "reports")
    assert json.loads((tmp_path / "reports" / "eval_dev.json").read_text())["n"] == 6
    rows = (tmp_path / "reports" / "errors_dev_noisy_zero_shot.csv").read_text().splitlines()
    assert rows == ["ROW_ID,error", "3,FP", "4,FP", "2,FN"]


def test_mixed_prompt_versions_are_an_error(dev_setup):
    derived, labels, preds = dev_setup
    ps = [pred(r, "no") for r in range(1, 7)]
    ps[0] = ps[0].model_copy(update={"prompt_hash": "new"})  # a rerun that stopped after 1 note
    write_preds(preds, "half_zero_shot_dev", ps)
    with pytest.raises(ValueError, match="more than one prompt version"):
        m.build_frame("dev", labels, preds, derived)


def test_round_selects_its_own_predictions(dev_setup):
    """One file holds two rounds; each round is scored from its own prompt hash only."""
    derived, labels, preds = dev_setup
    old = [pred(r, "yes") for r in range(1, 7)]
    new = [pred(r, "no").model_copy(update={"prompt_hash": "new"}) for r in range(1, 7)]
    write_preds(preds, "two_zero_shot_dev", old + new)
    for f in preds.glob("*.jsonl"):  # keep only the two-round file
        if f.name != "two_zero_shot_dev.jsonl":
            f.unlink()
    r_old = m.build_frame("dev", labels, preds, derived, {"zero_shot": "x", "few_shot": "x"})
    r_new = m.build_frame("dev", labels, preds, derived, {"zero_shot": "new", "few_shot": "new"})
    assert r_old["two_zero_shot|answer"].eq("yes").all()
    assert r_new["two_zero_shot|answer"].eq("no").all()
    with pytest.raises(ValueError, match="with prompt missing"):
        m.build_frame("dev", labels, preds, derived, {"zero_shot": "missing", "few_shot": "x"})


def test_round_outputs_go_to_round_folder(tmp_path):
    assert m.output_paths("dev", "r1", tmp_path) == (
        tmp_path / "rounds" / "dev_r1" / "eval.json", tmp_path / "rounds" / "dev_r1", "errors_")
    assert m.output_paths("test_a", None, tmp_path)[0] == tmp_path / "eval_test_a.json"


def test_gold_fingerprint_changes_with_labels():
    a = pd.DataFrame({"row_id": [1, 2], "gold": ["yes", "no"]})
    b = pd.DataFrame({"row_id": [2, 1], "gold": ["no", "yes"]})
    c = pd.DataFrame({"row_id": [1, 2], "gold": ["no", "no"]})
    assert m.gold_fingerprint(a) == m.gold_fingerprint(b) != m.gold_fingerprint(c)
