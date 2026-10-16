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


def test_label_two_notes(data_dir):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    assert not at.exception
    assert [o for o in at.radio(key="goc_11").options] == ["yes", "no", "unsure"]

    at.radio(key="goc_11").set_value("yes").run()
    at.button(key="save_11").click().run()
    at.radio(key="goc_12").set_value("unclear").run()   # app moved on to the next note
    at.button(key="save_12").click().run()
    assert not at.exception

    lines = (data_dir / "labels" / "dev_Z_TT.jsonl").read_text().splitlines()
    recs = [json.loads(line) for line in lines]
    assert [(r["row_id"], r["goc_present"]) for r in recs] == [(11, "yes"), (12, "unclear")]
    assert set(recs[0]) == {"row_id", "assignment", "goc_present", "annotator",
                            "minutes_spent", "labeled_at"}
    assert not any(t in "".join(lines) for t in NOTES.values())


def test_go_back_and_change_answer(data_dir):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    at.radio(key="goc_11").set_value("yes").run()
    at.button(key="save_11").click().run()            # moves on to note 2
    at.sidebar.button[0].click().run()                # ◀ Prev, back to note 1
    assert at.radio(key="goc_11").value == "yes"
    assert any("Saved answer" in m.value for m in at.info)
    at.radio(key="goc_11").set_value("no").run()
    assert any("not saved yet" in w.value for w in at.warning)
    at.button(key="save_11").click().run()
    assert not at.exception

    from src.labeling.collect import read_labels
    latest, problems = read_labels(data_dir / "labels" / "dev_Z_TT.jsonl")
    assert not problems and latest[11].goc_present == "no"   # latest save wins


def test_save_needs_an_answer(data_dir):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    at.button(key="save_11").click().run()
    assert any("Choose yes, no or unsure" in e.value for e in at.error)
    assert not (data_dir / "labels" / "dev_Z_TT.jsonl").exists()


def test_mismatched_notes_block_labeling(data_dir):
    a = pd.read_parquet(data_dir / "assignments" / "dev_Z.parquet")
    a["n_chars"] += 1
    a.to_parquet(data_dir / "assignments" / "dev_Z.parquet")
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="annotator").input("tt").run()
    assert any("doesn't match" in e.value for e in at.error)
