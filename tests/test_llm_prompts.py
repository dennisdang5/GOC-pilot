"""Prompt assembly and synthetic few-shot examples (synthetic strings only)."""

import json

import pytest

from src.llm.prompts import build_messages, load_fewshot, prompt_hash
from src.llm.schema import LLMOutput
from src.llm.validate import span_verified


def test_fewshot_examples_are_consistent():
    examples = load_fewshot()
    assert len(examples) == 16
    assert len({ex["id"] for ex in examples}) == 16
    assert all(ex["id"].startswith("syn_") for ex in examples)
    for ex in examples:
        out = LLMOutput.model_validate(ex["output"])
        # a yes example must quote its own note verbatim; a no example has no span
        assert span_verified(out.evidence_span, ex["note"]) is (True if out.goc_present == "yes" else None)
    labels = [ex["output"]["goc_present"] for ex in examples]
    assert (labels.count("yes"), labels.count("no")) == (6, 10)


@pytest.mark.parametrize("strategy, n_messages", [("zero_shot", 2), ("few_shot", 34)])
def test_build_messages_shape(strategy, n_messages):
    msgs = build_messages("Synthetic note {with braces}.", strategy)
    assert len(msgs) == n_messages
    assert msgs[0]["role"] == "system" and msgs[-1]["role"] == "user"
    assert "Synthetic note {with braces}." in msgs[-1]["content"]
    assert [m["role"] for m in msgs[1:-1]] == ["user", "assistant"] * ((n_messages - 2) // 2)


def test_fewshot_assistant_turns_are_schema_json():
    for m in build_messages("x", "few_shot"):
        if m["role"] == "assistant":
            assert list(json.loads(m["content"])) == ["evidence_span", "goc_present"]


def test_prompt_hash_stable_and_distinct():
    assert prompt_hash("zero_shot") == prompt_hash("zero_shot")
    assert prompt_hash("zero_shot") != prompt_hash("few_shot")
