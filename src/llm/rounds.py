"""Prompt-tuning rounds on dev: registry and per-round prompt snapshots.

A round is one version of the prompts (system.txt, user.txt, fewshot.jsonl) run on dev. Each
round is registered in src/llm/prompt_rounds/rounds.json (date, prompt hash per strategy, CARC
job, GPU, what changed), and a copy of its prompt files is kept in
src/llm/prompt_rounds/{round}/ so every round can be read back and re-hashed. The prompts are
synthetic, so they're safe to keep in the repo.

Workflow when the prompts change: add a new round (next id, new hashes, what changed), copy the
prompt files into its folder, run dev on CARC, then fill in carc_job.
tests/test_rounds.py checks that the current prompts match the newest round and that every
snapshot reproduces its recorded hashes.
"""

import json
from pathlib import Path

from src.llm.prompts import STRATEGIES, prompt_hash

ROUNDS_DIR = Path(__file__).resolve().parent / "prompt_rounds"
REGISTRY = ROUNDS_DIR / "rounds.json"


def load_rounds(path: Path = REGISTRY) -> dict[str, dict]:
    """Round id -> entry, in registry order (r0 first)."""
    return json.loads(path.read_text(encoding="utf-8"))


def current_round(rounds: dict[str, dict] | None = None) -> str | None:
    """The round whose hashes match the current prompts, or None if the prompts are unregistered."""
    rounds = load_rounds() if rounds is None else rounds
    now = {s: prompt_hash(s) for s in STRATEGIES}
    matches = [r for r, e in rounds.items() if e["prompt_hash"] == now]
    return matches[-1] if matches else None
