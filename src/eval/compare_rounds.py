"""Compare prompt-tuning rounds on dev: is tuning helping?

Run from the repo root (after scoring each round with src.eval.metrics --set dev --round rN):
  python -m src.eval.compare_rounds

Writes reports/rounds_dev.md. Reads only src/llm/prompt_rounds/rounds.json and the aggregate
reports/rounds/dev_{round}/eval.json files: no labels, predictions or note text. ROW_IDs in the
JSON are used to pair notes for McNemar and never appear in the output.

- Rounds are compared only on the same notes and the same gold labels (gold fingerprint). If the
  labels changed, re-score the older rounds with --rescore first.
- McNemar (exact) per config for each round vs the one before, Holm across the configs within
  each step. "better" / "worse" only when Holm p < 0.05; otherwise "comparable".
"""

import json
import sys
from pathlib import Path

from src.eval.metrics import REPORT_DIR, fmt, holm, mcnemar_p, output_paths
from src.eval.report_md import _f1, _pval, _table
from src.llm.rounds import load_rounds

OUT = REPORT_DIR / "rounds_dev.md"


def load_scored(rounds: dict[str, dict], report_dir: Path = REPORT_DIR) -> dict[str, dict]:
    """Round id -> eval JSON, for the rounds that have been scored (registry order)."""
    scored = {}
    for rid in rounds:
        path = output_paths("dev", rid, report_dir)[0]
        if path.exists():
            scored[rid] = json.loads(path.read_text(encoding="utf-8"))
    return scored


def check_comparable(scored: dict[str, dict]) -> None:
    fps = {rid: (r["gold_fingerprint"], tuple(r["row_ids"])) for rid, r in scored.items()}
    if len(set(fps.values())) > 1:
        raise ValueError("rounds were scored on different notes or gold labels: "
                         f"{ {rid: f[0] for rid, f in fps.items()} } "
                         "(re-score the older rounds with --rescore)")


def wrong(r: dict, config: str) -> set[int]:
    s = r["configs"][config]
    return set(s["false_positives"]) | set(s["false_negatives"])


def step_tests(prev: dict, new: dict) -> list[dict]:
    """Per config: notes only the previous / only the new round got right, exact McNemar, Holm."""
    rows = []
    for c in sorted(set(prev["configs"]) & set(new["configs"])):
        w_prev, w_new = wrong(prev, c), wrong(new, c)
        only_prev, only_new = len(w_new - w_prev), len(w_prev - w_new)
        rows.append({"config": c, "only_prev": only_prev, "only_new": only_new,
                     "p": mcnemar_p(only_prev, only_new)})
    return holm(rows)


def verdict(row: dict) -> str:
    if row["p_holm"] >= 0.05:
        return "comparable"
    return "better" if row["only_new"] > row["only_prev"] else "worse"


def _delta(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "NA"
    d = b - a
    return "0.00" if abs(d) < 0.005 else f"{d:+.2f}"


def _est(m: dict, key: str) -> float | None:
    v = m[key]
    return v if key == "f1" else (None if v is None else v["est"])


def render(rounds: dict[str, dict], scored: dict[str, dict]) -> str:
    ids = list(scored)
    L = ["# Prompt-tuning rounds: dev", "",
         "Each round is one version of the prompts run on the 30 dev notes. All rounds are scored "
         "against the same gold labels. Dev is for tuning: none of these numbers are reportable.",
         ""]

    L += ["## Rounds", ""]
    rows = []
    for rid, e in rounds.items():
        job = e["carc_job"] or "—"
        status = "" if rid in scored else " (not scored yet)"
        rows.append([f"**{rid}**{status}", e["date"], f"{job} ({e['gpu']})",
                     f"`{e['prompt_hash']['zero_shot']}`", f"`{e['prompt_hash']['few_shot']}`",
                     e["changes"]])
    L += _table(["round", "date", "CARC job (GPU)", "zero-shot prompt", "few-shot prompt",
                 "what changed"], rows) + [""]
    if not ids:
        return "\n".join(L + ["No round has been scored yet.", ""])

    newest = scored[ids[-1]]["configs"]
    order = sorted(newest, key=lambda c: -(newest[c]["primary"]["f1"] or -1))
    configs = order + sorted({c for r in scored.values() for c in r["configs"]} - set(order))

    L += ["## Results by round (primary rule)", "",
          "Proportions show the estimate and its 95% Wilson CI. Configs are sorted by F1 in the "
          f"newest round ({ids[-1]}).", ""]
    rows = []
    for c in configs:
        for rid in ids:
            s = scored[rid]["configs"].get(c)
            if s is None:
                continue
            m, y = s["primary"], s["spans"]["yes"]
            rows.append([f"`{c}`", rid, "{tp} / {fp} / {fn} / {tn}".format(**m),
                         fmt(m["sensitivity"]), fmt(m["ppv"]), fmt(m["specificity"]),
                         _f1(m["f1"]), _f1(s["strict"]["f1"]),
                         f"{y['verified']} / {y['spans']}"])
    L += _table(["config", "round", "TP / FP / FN / TN", "sensitivity (recall)",
                 "PPV (precision)", "specificity", "F1", "F1 strict", "quotes verified (yes)"],
                rows) + [""]

    if len(ids) < 2:
        L += ["Only one round has been scored, so there is nothing to compare yet.", ""]
    else:
        n_yes = scored[ids[-1]].get("gold", {}).get("yes", 0)
        one_note = f" One dev note moves sensitivity by about {1 / n_yes:.2f}." if n_yes else ""
        L += ["## Change from the previous round", "",
              "Point-estimate differences (new minus previous); `F1 vs r0` compares with the "
              "first round." + one_note, ""]
        rows = []
        first = ids[0]
        for c in configs:
            for prev, new in zip(ids, ids[1:]):
                a = scored[prev]["configs"].get(c)
                b = scored[new]["configs"].get(c)
                if a is None or b is None:
                    continue
                pa, pb = a["primary"], b["primary"]
                base = scored[first]["configs"].get(c)
                rows.append([f"`{c}`", f"{prev} → {new}",
                             f"{pb['fp'] - pa['fp']:+d}", f"{pb['fn'] - pa['fn']:+d}",
                             *(_delta(_est(pa, k), _est(pb, k))
                               for k in ("sensitivity", "ppv", "specificity", "f1")),
                             _delta(base["primary"]["f1"], pb["f1"]) if base else "NA"])
        L += _table(["config", "step", "Δ FP", "Δ FN", "Δ sensitivity", "Δ PPV",
                     "Δ specificity", "Δ F1", "F1 vs r0"], rows) + [""]

        L += ["## Did each step help? (exact McNemar, Holm across configs within each step)", "",
              "Counts are notes only the previous round or only the new round got right. "
              "\"better\" / \"worse\" need Holm p < 0.05; otherwise the rounds are comparable.",
              ""]
        rows = []
        for prev, new in zip(ids, ids[1:]):
            for t in step_tests(scored[prev], scored[new]):
                rows.append([f"`{t['config']}`", f"{prev} → {new}", t["only_prev"],
                             t["only_new"], _pval(t["p"]), _pval(t["p_holm"]), verdict(t)])
        L += _table(["config", "step", "only previous right", "only new right", "p", "Holm p",
                     ""], rows) + [""]

    latest = scored[ids[-1]]
    n_pos = latest.get("gold", {}).get("yes", 0)
    step = f"{1 / n_pos:.2f}" if n_pos else "NA"
    L += ["## How to read this", "",
          f"- Same {latest.get('n', 30)} dev notes and the same gold labels for every round (current "
          "labels, including all revisions logged in CLAUDE.md §3.6).",
          f"- Dev has {n_pos} gold positives: one note moves sensitivity by about {step}, so most "
          "round-to-round changes are within noise. Rely on the McNemar column, not the deltas.",
          "- Prompts were tuned on these same notes, so later rounds are optimistic on dev. "
          "Only the frozen test sets give reportable numbers.",
          "- Per-round details: `reports/rounds/dev_{round}/results.md`. Prompt files of each "
          "round: `src/llm/prompt_rounds/{round}/`.", ""]
    return "\n".join(L)


def main() -> int:
    rounds = load_rounds()
    scored = load_scored(rounds)
    try:
        check_comparable(scored)
    except ValueError as e:
        print(f"compare_rounds: {e}")
        return 1
    OUT.write_text(render(rounds, scored), encoding="utf-8")
    print(f"wrote reports/{OUT.name} ({len(scored)} of {len(rounds)} rounds scored: "
          f"{', '.join(scored) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
