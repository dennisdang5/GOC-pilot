"""Dev triage viewer on synthetic notes, labels and predictions (no MIMIC data)."""

import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.eval import triage_app as t
from src.llm.schema import Prediction

APP = str(Path(__file__).resolve().parents[1] / "src" / "eval" / "triage_app.py")

NOTES = {
    1: "Met with daughter (HCP). Discussed poor prognosis; she wants comfort care.",
    2: "Palliative care consulted. Code status: DNR.",
    3: "Family meeting planned for tomorrow.",
    4: "Pt stable overnight. Full code.",
}
GOLD = {1: "yes", 2: "no", 3: "no", 4: "no"}


def pred(row_id, answer, span=None, strategy="zero_shot"):
    verified = None if span is None else " ".join(span.split()) in " ".join(NOTES[row_id].split())
    return Prediction(row_id=row_id, method="fake:1b", strategy=strategy, set="dev",
                      goc_present=answer, evidence_span=span, span_verified=verified,
                      prompt_hash="x", prompt_tokens=10, truncated=False, latency_s=0.1,
                      raw_output_path="raw")


@pytest.fixture
def base(tmp_path, monkeypatch):
    (tmp_path / "derived").mkdir()
    pd.DataFrame({"ROW_ID": list(NOTES), "stratum": ["cues_present"] * 3 + ["cues_missing"]}
                 ).to_parquet(tmp_path / "derived" / "dev_sample.parquet")
    pd.DataFrame({"ROW_ID": list(NOTES), "TEXT": list(NOTES.values())}).to_parquet(
        tmp_path / "derived" / "candidates.parquet")
    (tmp_path / "labels").mkdir()
    lines = [json.dumps({"row_id": r, "assignment": "dev_A", "goc_present": g,
                         "annotator": "ZZ", "labeled_at": "2026-10-29T00:00:00+00:00"})
             for r, g in GOLD.items()]
    (tmp_path / "labels" / "dev_A_ZZ.jsonl").write_text("\n".join(lines) + "\n")
    (tmp_path / "predictions").mkdir()
    # a: FP on 2 and 3. b: FP on 2, FN on 1. Note 4 is right for both.
    runs = {"a_zero_shot": [pred(1, "yes", "prognosis;  she wants"), pred(2, "yes", "Palliative"),
                            pred(3, "yes", "not in note"), pred(4, "no")],
            "b_zero_shot": [pred(1, "no"), pred(2, "yes", "Code status: DNR"), pred(3, "no"),
                            pred(4, "no")]}
    for stem, ps in runs.items():
        (tmp_path / "predictions" / f"{stem}_dev.jsonl").write_text(
            "".join(p.model_dump_json() + "\n" for p in ps))
    (tmp_path / "rounds.json").write_text(json.dumps(
        {"r0": {"date": "2026-10-29", "prompt_hash": {"zero_shot": "x", "few_shot": "x"},
                "carc_job": None, "gpu": "A100", "changes": "baseline"},
         "r1": {"date": "2026-11-09", "prompt_hash": {"zero_shot": "y", "few_shot": "y"},
                "carc_job": None, "gpu": "A100", "changes": "not run"}}))
    monkeypatch.setenv("GOC_TRIAGE_DIR", str(tmp_path))
    return tmp_path


def test_span_ranges_match_across_whitespace():
    text = "Discussed poor\nprognosis with  wife."
    assert t.span_ranges(text, "poor prognosis with") == [(10, 29)]
    assert t.span_ranges(text, None) == [] and t.span_ranges(text, "  ") == []
    assert t.span_ranges(text, "absent") == []


def test_highlight_escapes_and_merges():
    out = t.highlight("a <b> c d", [(2, 5), (4, 7), (8, 9)])
    assert out == "a <mark>&lt;b&gt; c</mark> <mark>d</mark>"


def test_error_table_ranks_most_missed_first(base):
    from src.eval.metrics import build_frame
    df = build_frame("dev", base / "labels", base / "predictions", base / "derived",
                     {"zero_shot": "x", "few_shot": "x"})
    e = t.error_table(df)
    assert e["row_id"].tolist() == [2, 1, 3]          # 2 wrong in 2 configs, then 1 and 3
    assert e["n_wrong"].tolist() == [2, 1, 1]
    row1 = e[e["row_id"] == 1].iloc[0]
    assert row1["a_zero_shot|outcome"] == "TP" and row1["b_zero_shot|outcome"] == "FN"


def test_app_shows_errors_and_saves_pattern(base):
    labels_before = (base / "labels" / "dev_A_ZZ.jsonl").read_text()
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert at.warning and "r1" in at.warning[0].value  # newest round has no predictions yet
    at.selectbox(key="round").select("r0").run()
    assert not at.exception
    assert "ROW_ID 2" in at.subheader[0].value
    assert "<mark>Palliative</mark>" in at.markdown[0].value
    assert "<mark>Code status: DNR</mark>" in at.markdown[0].value

    at.text_area(key="pattern_r0_2").input("consult only, no talk").run()
    at.button(key="save_r0_2").click().run()
    assert not at.exception
    lines = (base / "triage" / "dev_r0_patterns.jsonl").read_text().splitlines()
    saved = [json.loads(x) for x in lines]
    assert saved[-1]["row_id"] == 2 and saved[-1]["pattern"] == "consult only, no talk"
    assert (base / "labels" / "dev_A_ZZ.jsonl").read_text() == labels_before  # never writes labels

    at.selectbox(key="only").select("b_zero_shot").run()
    assert not at.exception
    assert len(at.radio(key="note_r0_b_zero_shot").options) == 2  # notes 2 and 1


def test_triage_is_dev_only():
    assert t.SET == "dev"
