"""End-to-end run of the Streamlit labeling app on synthetic notes (no MIMIC data)."""

import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "labeling" / "app.py")

NOTES = {
    11: "Family meeting held with wife and son. They want to focus on comfort.",
    12: "Code status: DNR. No discussion documented today.",
}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    (tmp_path / "parquet").mkdir()
    (tmp_path / "assignments").mkdir()
    pd.DataFrame({"ROW_ID": list(NOTES), "TEXT": list(NOTES.values())}).to_parquet(
        tmp_path / "parquet" / "noteevents.parquet")
    pd.DataFrame({"ROW_ID": list(NOTES), "CATEGORY": ["Physician ", "General"],
                  "n_chars": [len(t) for t in NOTES.values()], "label_order": [1, 2]}
                 ).to_parquet(tmp_path / "assignments" / "dev_Z.parquet")
    monkeypatch.setenv("GOC_DATA_DIR", str(tmp_path))
    return tmp_path


def test_label_one_note(data_dir):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    assert not at.exception

    at.radio(key="goc_11").set_value("yes").run()
    at.text_area(key="evidence_11").input("Family meeting held with wife and son.")
    at.run()
    at.button(key="save_11").click().run()
    assert not at.exception

    lines = (data_dir / "labels" / "dev_Z_TT.jsonl").read_text().splitlines()
    rec = json.loads(lines[-1])
    assert rec["row_id"] == 11 and rec["goc_present"] == "yes"
    assert NOTES[11][rec["evidence_start"]:rec["evidence_end"]] == \
        "Family meeting held with wife and son."
    # no note text in the label file
    assert all(isinstance(v, (int, float, bool, list, type(None))) or k in
               {"assignment", "goc_present", "negative_reason", "annotator", "labeled_at"}
               for k, v in rec.items())
    assert "Family meeting held" not in lines[-1]


def test_label_no_with_reason(data_dir):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    at.sidebar.selectbox[1].set_value(1).run()          # "Go to note" -> note 2 (ROW_ID 12)
    at.radio(key="goc_12").set_value("no").run()
    at.selectbox(key="neg_12").set_value("order_only").run()
    at.button(key="save_12").click().run()
    assert not at.exception
    rec = json.loads((data_dir / "labels" / "dev_Z_TT.jsonl").read_text().splitlines()[-1])
    assert rec["row_id"] == 12 and rec["goc_present"] == "no"
    assert rec["negative_reason"] == "order_only" and rec["evidence_start"] is None


def test_mismatched_notes_block_labeling(data_dir):
    a = pd.read_parquet(data_dir / "assignments" / "dev_Z.parquet")
    a["n_chars"] += 1
    a.to_parquet(data_dir / "assignments" / "dev_Z.parquet")
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    assert any("doesn't match" in e.value for e in at.error)
