"""Run one model x strategy over one set with a local Ollama server.

Run from the repo root:
  python -m src.llm.run --model llama3.1:8b --strategy zero_shot --set dev [--limit 3]
  python -m src.llm.run --freeze      # record current prompt hashes; unlocks test_a / test_b

Writes data/predictions/{model}_{strategy}_{set}.jsonl (append-only, latest per ROW_ID wins) and
raw model replies to data/predictions/raw/{model}_{strategy}_{set}/{prompt_hash}/{ROW_ID}.json.
Resumable: ROW_IDs whose latest prediction is error-free AND made with the current prompt hash are
skipped, so a prompt change reruns every note into the same file (older lines stay as history).
Raw replies from before 2026-11-09 sit directly under the stem folder, without a hash folder.

Prints counts, latency, error types and ROW_IDs only. No note text or model output.

Context: num_ctx is set on every call (Ollama otherwise truncates silently). Before each call
the prompt length is estimated conservatively from characters; a note that might not fit is not
sent and is recorded with error "truncated". After the call, done_reason "length" (output cut off)
is also recorded.

Test sets are refused unless src/llm/prompts/FROZEN matches the current prompt hashes.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import ValidationError

from src.llm.notes import load_notes, set_row_ids
from src.llm.prompts import PROMPT_DIR, STRATEGIES, build_messages, prompt_hash
from src.llm.schema import LLMOutput, Prediction
from src.llm.validate import read_predictions, span_verified

ROOT = Path(__file__).resolve().parents[2]
PRED_DIR = ROOT / "data" / "predictions"
FROZEN_PATH = PROMPT_DIR / "FROZEN"

HOST = "http://localhost:11434"
NUM_CTX = 12288
NUM_PREDICT = 400
SEED = 20261028
CHARS_PER_TOKEN = 2.5  # conservative for MIMIC text (abbreviations, punctuation)


def file_stem(model: str, strategy: str, set_name: str) -> str:
    return f"{model.replace(':', '-').replace('/', '_')}_{strategy}_{set_name}"


def freeze(path: Path = FROZEN_PATH) -> dict:
    record = {s: prompt_hash(s) for s in STRATEGIES}
    record["frozen_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def check_frozen(set_name: str, strategy: str, path: Path = FROZEN_PATH) -> None:
    """Raise unless set is dev, or the prompts are frozen and unchanged since freezing."""
    if set_name == "dev":
        return
    if not path.exists():
        raise PermissionError(f"{set_name} is frozen: prompts not frozen yet (no {path.name})")
    if json.loads(path.read_text(encoding="utf-8")).get(strategy) != prompt_hash(strategy):
        raise PermissionError(f"{set_name}: {strategy} prompt changed since it was frozen")


def fits(messages: list[dict], num_ctx: int = NUM_CTX) -> bool:
    n_chars = sum(len(m["content"]) for m in messages)
    return n_chars / CHARS_PER_TOKEN + NUM_PREDICT <= num_ctx


def call_ollama(session, host: str, model: str, messages: list[dict], num_ctx: int) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": LLMOutput.model_json_schema(),
        "options": {"temperature": 0, "seed": SEED, "num_ctx": num_ctx,
                    "num_predict": NUM_PREDICT},
        "keep_alive": "10m",
    }
    if model.startswith("qwen3"):
        payload["think"] = False
    resp = session.post(f"{host}/api/chat", json=payload, timeout=600)
    resp.raise_for_status()
    return resp.json()


def predict_one(session, host, model, strategy, set_name, row_id, note, raw_dir, num_ctx, phash):
    messages = build_messages(note, strategy)
    raw_path = raw_dir / f"{row_id}.json"
    base = dict(row_id=row_id, method=model, strategy=strategy, set=set_name, prompt_hash=phash,
                raw_output_path=raw_path.relative_to(ROOT).as_posix()
                if raw_path.is_relative_to(ROOT) else raw_path.as_posix())
    if not fits(messages, num_ctx):
        return Prediction(**base, goc_present=None, evidence_span=None, span_verified=None,
                          prompt_tokens=None, truncated=True, latency_s=0.0, error="truncated")
    t0 = time.perf_counter()
    data = call_ollama(session, host, model, messages, num_ctx)
    latency = time.perf_counter() - t0
    raw_path.write_text(json.dumps(data), encoding="utf-8")
    cut_off = data.get("done_reason") == "length"
    try:
        out = LLMOutput.model_validate_json(data["message"]["content"])
    except (ValidationError, KeyError, TypeError):
        out = None
    error = "truncated" if cut_off else "parse" if out is None else None
    return Prediction(**base,
                      goc_present=out.goc_present if out and not error else None,
                      evidence_span=out.evidence_span if out else None,
                      span_verified=span_verified(out.evidence_span, note) if out else None,
                      prompt_tokens=data.get("prompt_eval_count"), truncated=cut_off,
                      latency_s=round(latency, 2), error=error)


def run(model, strategy, set_name, row_ids, notes, session, host=HOST, num_ctx=NUM_CTX,
        pred_dir=PRED_DIR) -> dict:
    stem = file_stem(model, strategy, set_name)
    phash = prompt_hash(strategy)
    out_path, raw_dir = pred_dir / f"{stem}.jsonl", pred_dir / "raw" / stem / phash
    raw_dir.mkdir(parents=True, exist_ok=True)
    done = {r for r, p in read_predictions(out_path).items()
            if p.error is None and p.prompt_hash == phash}
    todo = [r for r in row_ids if r not in done]
    summary = {"skipped": len(row_ids) - len(todo), "ok": 0, "errors": {}, "latency": []}
    with out_path.open("a", encoding="utf-8") as f:
        for i, row_id in enumerate(todo, start=1):
            pred = predict_one(session, host, model, strategy, set_name, row_id, notes[row_id],
                               raw_dir, num_ctx, phash)
            f.write(pred.model_dump_json() + "\n")
            f.flush()
            if pred.error:
                summary["errors"].setdefault(pred.error, []).append(row_id)
            else:
                summary["ok"] += 1
                summary["latency"].append(pred.latency_s)
            if i % 10 == 0:
                print(f"  {i}/{len(todo)}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--strategy", choices=STRATEGIES)
    ap.add_argument("--set", dest="set_name", choices=["dev", "test_a", "test_b"])
    ap.add_argument("--limit", type=int, help="first N ROW_IDs only (smoke test)")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()

    if args.freeze:
        print("frozen:", json.dumps(freeze()))
        return 0
    if not (args.model and args.strategy and args.set_name):
        ap.error("--model, --strategy and --set are required")
    try:
        check_frozen(args.set_name, args.strategy)
    except PermissionError as e:
        print(f"refused: {e}")
        return 1

    row_ids = set_row_ids(args.set_name)[: args.limit]
    notes = load_notes(row_ids)
    print(f"{args.model} {args.strategy} {args.set_name}: {len(row_ids)} notes, "
          f"num_ctx={NUM_CTX}, prompt {prompt_hash(args.strategy)}")
    try:
        with requests.Session() as session:
            s = run(args.model, args.strategy, args.set_name, row_ids, notes, session, args.host)
    except requests.RequestException as e:
        print(f"aborted: {type(e).__name__} talking to Ollama at {args.host}")
        return 1
    lat = s["latency"]
    mean = f"{sum(lat) / len(lat):.1f}s" if lat else "-"
    print(f"skipped {s['skipped']} | ok {s['ok']} | mean latency {mean}")
    for err, ids in s["errors"].items():
        print(f"  {err}: {len(ids)} {ids}")
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
