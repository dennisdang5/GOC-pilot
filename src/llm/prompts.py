"""Prompt assembly for the two strategies.

zero_shot: system + user(note).
few_shot:  system + 3 synthetic examples as prior user/assistant turns + user(note).

Both share the same system and user text, so the strategies differ only by the examples.
Few-shot examples are synthetic (src/llm/fewshot.jsonl) and never come from MIMIC.
prompt_hash() covers every text that reaches the model except the note, and is recorded with each
prediction and checked by the test-set freeze guard.
"""

import hashlib
import json
from pathlib import Path
from typing import Literal

from src.llm.schema import LLMOutput

LLM_DIR = Path(__file__).resolve().parent
PROMPT_DIR = LLM_DIR / "prompts"
FEWSHOT_PATH = LLM_DIR / "fewshot.jsonl"

Strategy = Literal["zero_shot", "few_shot"]
STRATEGIES: tuple[Strategy, ...] = ("zero_shot", "few_shot")


def _read(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def load_fewshot() -> list[dict]:
    lines = FEWSHOT_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def user_turn(note: str) -> str:
    # str.replace, not str.format: notes can contain braces
    return _read("user.txt").replace("{note}", note)


def build_messages(note: str, strategy: Strategy) -> list[dict]:
    messages = [{"role": "system", "content": _read("system.txt")}]
    if strategy == "few_shot":
        for ex in load_fewshot():
            out = LLMOutput.model_validate(ex["output"])
            messages += [{"role": "user", "content": user_turn(ex["note"])},
                         {"role": "assistant", "content": out.model_dump_json()}]
    messages.append({"role": "user", "content": user_turn(note)})
    return messages


def prompt_hash(strategy: Strategy) -> str:
    """Short hash of everything the model sees except the note."""
    sentinel = "\x00NOTE\x00"
    payload = json.dumps(build_messages(sentinel, strategy), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
