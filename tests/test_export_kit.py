"""Labeling kit export + the app running from the kit layout (synthetic notes only)."""

import json

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.labeling.export_kit import export

TEXT = "Met with daughter (HCP); she says he would not want intubation."


def test_kit_export_and_label(tmp_path):
    src = tmp_path / "src_assign"
    src.mkdir()
    pd.DataFrame({"ROW_ID": [7], "CATEGORY": ["Physician "], "n_chars": [len(TEXT)],
                  "label_order": [1], "stratum": ["cues_present"]}
                 ).to_parquet(src / "dev_Z.parquet")
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "labels").mkdir()
    (kit / "labels" / "dev_Q_XX.jsonl").write_text("keep me\n")

    written = export(kit, src)
    assert "assignments/dev_Z.csv" in written and ".labeling-kit" in written
    assert "stratum" not in pd.read_csv(kit / "assignments" / "dev_Z.csv").columns
    assert (kit / "labels" / "dev_Q_XX.jsonl").read_text() == "keep me\n"  # labels untouched

    (kit / "data" / "parquet").mkdir(parents=True)
    pd.DataFrame({"ROW_ID": [7], "TEXT": [TEXT]}).to_parquet(
        kit / "data" / "parquet" / "noteevents.parquet")

    at = AppTest.from_file(str(kit / "src" / "labeling" / "app.py"), default_timeout=30).run()
    at.text_input(key="annotator").input("ab").run()
    at.selectbox(key="assignment").set_value("dev_Z").run()
    at.radio(key="interaction_7").set_value("yes")
    at.multiselect(key="participants_7").set_value(["surrogate"])
    at.radio(key="content_7").set_value("yes")
    at.text_area(key="evidence_7").input("he would not want intubation.")
    at.selectbox(key="gtype_7").set_value("acp_general")
    at.run()
    at.button(key="save_7").click().run()
    assert not at.exception

    rec = json.loads((kit / "labels" / "dev_Z_AB.jsonl").read_text().splitlines()[-1])
    assert rec["goc_present"] == "yes"
    assert TEXT[rec["evidence_start"]:rec["evidence_end"]] == "he would not want intubation."
