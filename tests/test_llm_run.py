"""LLM runner against a mocked Ollama, freeze guard, note loader (synthetic data only)."""

import json

import pandas as pd
import pytest

from src.llm import run as runmod
from src.llm.notes import load_notes, set_row_ids
from src.llm.validate import read_predictions

NOTES = {
    1: "Family meeting with wife; discussed poor prognosis and comfort care.",
    2: "Code status: DNR. Palliative care consulted.",
    3: "Pneumonia, on ceftriaxone.",
}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    """Answers per ROW_ID, found by which synthetic note is in the last user turn."""

    def __init__(self, replies):
        self.replies, self.payloads = replies, []

    def post(self, url, json, timeout):
        self.payloads.append(json)
        last = json["messages"][-1]["content"]
        row_id = next(r for r, t in NOTES.items() if t in last)
        content, reason = self.replies[row_id]
        return FakeResponse({"message": {"content": content}, "done_reason": reason,
                             "prompt_eval_count": 900})


def reply(span, goc):
    return json.dumps({"evidence_span": span, "goc_present": goc}), "stop"


def test_run_writes_predictions_and_resumes(tmp_path):
    replies = {
        1: reply("discussed poor prognosis", "yes"),
        2: ('{"evidence_span": null, "goc_present": "unclear"}', "stop"),   # not allowed -> parse
        3: reply("made-up quote", "yes"),
    }
    session = FakeSession(replies)
    s = runmod.run("qwen3:8b", "few_shot", "dev", [1, 2, 3], NOTES, session, pred_dir=tmp_path)
    assert s["ok"] == 2 and s["errors"] == {"parse": [2]}

    payload = session.payloads[0]
    assert payload["options"]["num_ctx"] == runmod.NUM_CTX
    assert payload["options"]["temperature"] == 0
    assert payload["think"] is False
    assert list(payload["format"]["properties"]) == ["evidence_span", "goc_present"]

    preds = read_predictions(tmp_path / "qwen3-8b_few_shot_dev.jsonl")
    assert preds[1].goc_present == "yes" and preds[1].span_verified is True
    assert preds[2].goc_present is None and preds[2].error == "parse"
    assert preds[3].span_verified is False
    phash = runmod.prompt_hash("few_shot")
    assert (tmp_path / "raw" / "qwen3-8b_few_shot_dev" / phash / "1.json").exists()

    # resume: only the errored ROW_ID is retried
    session2 = FakeSession({**replies, 2: reply(None, "no")})
    s2 = runmod.run("qwen3:8b", "few_shot", "dev", [1, 2, 3], NOTES, session2, pred_dir=tmp_path)
    assert s2["skipped"] == 2 and s2["ok"] == 1 and len(session2.payloads) == 1
    assert read_predictions(tmp_path / "qwen3-8b_few_shot_dev.jsonl")[2].goc_present == "no"


def test_prompt_change_reruns_all_notes(tmp_path, monkeypatch):
    replies = {r: reply(None, "no") for r in (1, 2, 3)}
    runmod.run("qwen3:8b", "few_shot", "dev", [1, 2, 3], NOTES, FakeSession(replies),
               pred_dir=tmp_path)
    monkeypatch.setattr(runmod, "prompt_hash", lambda strategy: "newhash")
    session = FakeSession(replies)
    s = runmod.run("qwen3:8b", "few_shot", "dev", [1, 2, 3], NOTES, session, pred_dir=tmp_path)
    assert s["skipped"] == 0 and s["ok"] == 3 and len(session.payloads) == 3
    preds = read_predictions(tmp_path / "qwen3-8b_few_shot_dev.jsonl")
    assert {p.prompt_hash for p in preds.values()} == {"newhash"}
    lines = (tmp_path / "qwen3-8b_few_shot_dev.jsonl").read_text().splitlines()
    assert len(lines) == 6  # the old round stays in the file as history
    assert (tmp_path / "raw" / "qwen3-8b_few_shot_dev" / "newhash" / "1.json").exists()


def test_think_flag_only_for_qwen3(tmp_path):
    session = FakeSession({1: reply(None, "no")})
    runmod.run("llama3.1:8b", "zero_shot", "dev", [1], NOTES, session, pred_dir=tmp_path)
    assert "think" not in session.payloads[0]


def test_output_cut_off_is_truncated(tmp_path):
    session = FakeSession({1: ('{"evidence_span": "Family meet', "length")})
    s = runmod.run("gemma3:4b", "zero_shot", "dev", [1], NOTES, session, pred_dir=tmp_path)
    assert s["errors"] == {"truncated": [1]}


def test_overlong_note_is_not_sent(tmp_path):
    notes = {1: NOTES[1] + " x" * 20000}
    session = FakeSession({})
    s = runmod.run("gemma3:4b", "zero_shot", "dev", [1], notes, session, num_ctx=4096,
                   pred_dir=tmp_path)
    assert s["errors"] == {"truncated": [1]} and session.payloads == []


def test_freeze_guard(tmp_path):
    frozen = tmp_path / "FROZEN"
    runmod.check_frozen("dev", "zero_shot", frozen)                    # dev always allowed
    with pytest.raises(PermissionError):
        runmod.check_frozen("test_a", "zero_shot", frozen)             # not frozen yet
    runmod.freeze(frozen)
    runmod.check_frozen("test_b", "few_shot", frozen)                  # frozen and unchanged
    record = json.loads(frozen.read_text())
    record["few_shot"] = "000000000000"                                # prompt edited later
    frozen.write_text(json.dumps(record))
    with pytest.raises(PermissionError):
        runmod.check_frozen("test_b", "few_shot", frozen)


def test_note_loader(tmp_path):
    pd.DataFrame({"ROW_ID": [30, 10]}).to_parquet(tmp_path / "dev_sample.parquet")
    pd.DataFrame({"ROW_ID": [10, 20, 30], "TEXT": ["a", "b", "c"]}).to_parquet(
        tmp_path / "candidates.parquet")
    assert set_row_ids("dev", tmp_path) == [10, 30]
    assert load_notes([10, 30], tmp_path) == {10: "a", 30: "c"}
    with pytest.raises(KeyError, match="99"):
        load_notes([10, 99], tmp_path)
