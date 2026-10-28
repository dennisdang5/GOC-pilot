"""LLM output and prediction schemas (pydantic).

LLMOutput is what the model must return. Ollama's structured output constrains decoding to its
JSON schema, and the result is validated again here. Field order matters: the model quotes its
evidence first, then decides. Models answer yes / no only (no "unclear"; decided 2026-10-28).

Prediction is the record written per note to data/predictions/. evidence_span is note text, so
prediction files stay under data/ and are never printed.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_span: str | None  # verbatim quote from the note, null if none
    goc_present: Literal["yes", "no"]


class Prediction(BaseModel):
    row_id: int
    method: str                 # Ollama model tag, e.g. "llama3.1:8b"
    strategy: Literal["zero_shot", "few_shot"]
    set: Literal["dev", "test_a", "test_b"]
    goc_present: Literal["yes", "no"] | None  # None only when error is set
    evidence_span: str | None
    span_verified: bool | None  # None when there is no span
    prompt_hash: str
    prompt_tokens: int | None
    truncated: bool
    latency_s: float
    raw_output_path: str
    error: str | None = None    # "parse" | "truncated" | "http"; class names only, never text
