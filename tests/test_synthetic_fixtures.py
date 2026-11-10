"""Format check for tests/fixtures/synthetic_notes.jsonl (hand-written fake notes, safe to read).

One JSON object per line:
  {"id": "syn_001", "pattern": "palliative_consulted_no_talk", "expected_goc": "yes" | "no",
   "error_type": "FP" | "FN", "text": "..."}
No ROW_IDs or other links to real notes (user decision 2026-11-09).
"""

import json
import re
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_notes.jsonl"
FIELDS = {"id", "pattern", "expected_goc", "error_type", "text"}


def records() -> list[dict]:
    if not FIXTURE.exists():
        return []
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines()
            if line.strip()]


@pytest.mark.skipif(not FIXTURE.exists(), reason="no synthetic notes written yet")
def test_synthetic_notes_format():
    recs = records()
    assert recs, "file exists but is empty"
    ids = [r.get("id") for r in recs]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for r in recs:
        assert set(r) == FIELDS, (r.get("id"), sorted(set(r) ^ FIELDS))
        assert re.fullmatch(r"syn_\d{3}", r["id"]), r["id"]
        assert re.fullmatch(r"[a-z0-9_]+", r["pattern"]), r["id"]
        assert r["expected_goc"] in {"yes", "no"}, r["id"]
        assert r["error_type"] in {"FP", "FN"}, r["id"]
        # an FP fixture imitates a model yes on a gold-no note, and vice versa
        assert (r["error_type"] == "FP") == (r["expected_goc"] == "no"), r["id"]
        assert r["text"].strip(), r["id"]
