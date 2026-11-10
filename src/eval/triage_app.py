"""Local dev error triage viewer (Streamlit). Runs on this computer only; never upload note text.

Run from the repo root:  streamlit run src/eval/triage_app.py

Dev set only (the test sets stay frozen). Lists every dev note that at least one config got wrong
under the primary rule, most-missed first. For each note it shows the gold label, every config's
answer, whether its quote was verified, and the note text with the quotes highlighted. A free-text
pattern box saves to data/triage/dev_patterns.jsonl (gitignored, append-only, latest per ROW_ID
wins). The pattern file is for the user's own notes; Claude never reads it. Never writes labels.

Set GOC_TRIAGE_DIR to a folder holding derived/, predictions/, labels/ and triage/ to run on
synthetic data (used by the tests).
"""

import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # `streamlit run` doesn't put the repo root on the path
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src.eval.metrics import LABELS_DIR, build_frame, configs_in, load_configs  # noqa: E402
from src.llm.notes import DERIVED, load_notes  # noqa: E402
from src.llm.validate import PRED_DIR  # noqa: E402

SET = "dev"  # hard-coded: triage never touches test_a / test_b

if "GOC_TRIAGE_DIR" in os.environ:
    BASE = Path(os.environ["GOC_TRIAGE_DIR"])
    DERIVED_DIR, PRED_PATH, LABELS_PATH = BASE / "derived", BASE / "predictions", BASE / "labels"
    TRIAGE_DIR = BASE / "triage"
else:
    DERIVED_DIR, PRED_PATH, LABELS_PATH = DERIVED, PRED_DIR, LABELS_DIR
    TRIAGE_DIR = ROOT / "data" / "triage"
PATTERNS = TRIAGE_DIR / f"{SET}_patterns.jsonl"


# ---------- data ----------

def error_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per note with >=1 wrong config: row_id, stratum, gold, n_wrong, and per config
    '{config}|outcome' in TP / FP / FN / TN. Primary rule: gold unclear -> no, failure -> no."""
    gold_yes = df["gold"].eq("yes")
    out = df[["row_id", "stratum", "gold"]].copy()
    configs = configs_in(df)
    for c in configs:
        pred_yes = df[f"{c}|answer"].eq("yes")
        out[f"{c}|outcome"] = [("T" if g == p else "F") + ("P" if p else "N")
                               for g, p in zip(gold_yes, pred_yes)]
    out["n_wrong"] = out[[f"{c}|outcome" for c in configs]].isin(["FP", "FN"]).sum(axis=1)
    out = out[out["n_wrong"] > 0]
    return out.sort_values(["n_wrong", "row_id"], ascending=[False, True], ignore_index=True)


def span_ranges(text: str, span: str | None) -> list[tuple[int, int]]:
    """Character ranges where the quote occurs, matching any whitespace between its words."""
    words = (span or "").split()
    if not words:
        return []
    pattern = r"\s+".join(re.escape(w) for w in words)
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]


def highlight(text: str, ranges: list[tuple[int, int]]) -> str:
    """HTML-escaped text with the (merged) ranges wrapped in <mark>."""
    merged: list[list[int]] = []
    for s, e in sorted(ranges):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    parts, pos = [], 0
    for s, e in merged:
        parts += [html.escape(text[pos:s]), f"<mark>{html.escape(text[s:e])}</mark>"]
        pos = e
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def read_patterns(path: Path) -> dict[int, str]:
    latest: dict[int, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                latest[int(rec["row_id"])] = rec["pattern"]
    return latest


def save_pattern(path: Path, row_id: int, pattern: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"row_id": row_id, "pattern": pattern,
           "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


@st.cache_data
def load_all() -> tuple[pd.DataFrame, dict, dict[int, str]]:
    df = build_frame(SET, LABELS_PATH, PRED_PATH, DERIVED_DIR)
    errors = error_table(df)
    preds = load_configs(SET, PRED_PATH)
    notes = load_notes(errors["row_id"].tolist(), DERIVED_DIR)
    return errors, preds, notes


# ---------- UI ----------

def note_html(body: str) -> str:
    return ("<div style='height:65vh;overflow-y:auto;white-space:pre-wrap;font-family:monospace;"
            f"font-size:0.85rem;border:1px solid #8884;padding:0.75rem'>{body}</div>")


def main() -> None:
    st.set_page_config(page_title="GOC dev triage", layout="wide")
    errors, preds, notes = load_all()
    configs = sorted(preds)
    patterns = read_patterns(PATTERNS)

    with st.sidebar:
        st.header("Dev error triage")
        only = st.selectbox("Show errors of", ["any config"] + configs, key="only")
        rows = errors if only == "any config" else \
            errors[errors[f"{only}|outcome"].isin(["FP", "FN"])].reset_index(drop=True)
        st.caption(f"{len(rows)} notes · {sum(r in patterns for r in rows['row_id'])} with a "
                   "pattern saved")
        labels = [f"{r.row_id} · gold {r.gold} · wrong {r.n_wrong}/{len(configs)}"
                  + (" ✓" if r.row_id in patterns else "") for r in rows.itertuples()]
        if not labels:
            st.info("No errors for this config.")
            return
        i = st.radio("Note", range(len(labels)), format_func=lambda j: labels[j],
                     key=f"note_{only}")

    r = rows.iloc[i]
    row_id = int(r["row_id"])
    st.subheader(f"ROW_ID {row_id} · gold: {r['gold']} · stratum: {r['stratum']} · "
                 f"wrong in {r['n_wrong']}/{len(configs)} configs")

    text, ranges, table = notes[row_id], [], []
    for c in configs:
        p = preds[c][row_id]
        ranges += span_ranges(text, p.evidence_span)
        table.append({"config": c, "answer": p.goc_present or f"failed ({p.error})",
                      "outcome": r[f"{c}|outcome"],
                      "quote": {True: "verified", False: "not found", None: "none"}[
                          p.span_verified],
                      "quote text": p.evidence_span or ""})
    st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    st.markdown(note_html(highlight(text, ranges)), unsafe_allow_html=True)

    pattern = st.text_area("Pattern (your words; stays in data/triage/, never shared)",
                           value=patterns.get(row_id, ""), key=f"pattern_{row_id}")
    if st.button("Save pattern", key=f"save_{row_id}"):
        save_pattern(PATTERNS, row_id, pattern)
        st.rerun()


if __name__ == "__main__":  # streamlit run and AppTest both run it as __main__
    main()
