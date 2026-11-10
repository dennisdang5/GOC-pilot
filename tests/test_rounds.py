"""Prompt-tuning round registry: every prompt version is registered and kept (synthetic prompts)."""

import re

from src.llm import prompts
from src.llm.rounds import ROUNDS_DIR, current_round, load_rounds


def snapshot_hashes(monkeypatch, rid):
    monkeypatch.setattr(prompts, "PROMPT_DIR", ROUNDS_DIR / rid)
    monkeypatch.setattr(prompts, "FEWSHOT_PATH", ROUNDS_DIR / rid / "fewshot.jsonl")
    return {s: prompts.prompt_hash(s) for s in prompts.STRATEGIES}


def test_round_ids_and_fields():
    rounds = load_rounds()
    assert list(rounds) == [f"r{i}" for i in range(len(rounds))]
    for rid, e in rounds.items():
        assert set(e) == {"date", "prompt_hash", "carc_job", "gpu", "changes"}, rid
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]), rid
        assert set(e["prompt_hash"]) == set(prompts.STRATEGIES), rid
        assert all(re.fullmatch(r"[0-9a-f]{12}", h) for h in e["prompt_hash"].values()), rid
        assert e["changes"].strip(), rid


def test_current_prompts_are_the_newest_round():
    """Editing a prompt without registering a new round fails here."""
    rounds = load_rounds()
    assert current_round(rounds) == list(rounds)[-1]


def test_every_snapshot_reproduces_its_hashes(monkeypatch):
    for rid, e in load_rounds().items():
        assert snapshot_hashes(monkeypatch, rid) == e["prompt_hash"], rid


def test_prompt_versions_are_distinct():
    hashes = [tuple(e["prompt_hash"].values()) for e in load_rounds().values()]
    assert len(hashes) == len(set(hashes))
