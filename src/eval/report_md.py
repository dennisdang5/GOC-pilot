"""Render reports/eval_{set}.json as a readable markdown summary.

Run from the repo root (after src.eval.metrics has written the JSON):
  python -m src.eval.report_md --set dev

Writes reports/results_{set}.md. Reads only the aggregate JSON: no labels, predictions or note
text. False-positive / false-negative ROW_IDs in the JSON are left out of the markdown.

A hand-written summary between SUMMARY_START and SUMMARY_END in the existing results file is
kept verbatim (placed under the title) when the file is re-rendered.
"""

import argparse
import json
import sys
from pathlib import Path

from src.eval.metrics import PARTS, REPORT_DIR, fmt

SUMMARY_START = "<!-- summary:start -->"
SUMMARY_END = "<!-- summary:end -->"

VARIANT_TEXT = {
    "primary": "gold `unclear` counted as `no`",
    "exclude_unclear": "notes with gold `unclear` removed",
    "strict": "a model `yes` without a verified evidence span counted as `no`",
}


def _f1(v: float | None) -> str:
    return "NA" if v is None else f"{v:.2f}"


def _pval(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def _table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def _ordered(configs: dict) -> list[str]:
    """Configs sorted by primary F1, best first (NA last)."""
    return sorted(configs, key=lambda c: -(configs[c]["primary"]["f1"] or -1))


def _gold_text(g: dict, unclear: bool = True) -> str:
    keys = ("yes", "no", "unclear") if unclear else ("yes", "no")
    return " · ".join(f"{k} {g.get(k, 0)}" for k in keys)


def _compact_strata(cfgs: dict, order: list[str]) -> list[str]:
    """One row per config: counts and specificity per stratum (no per-stratum sens / PPV)."""
    rank = {"cues_present": 0, "cues_missing": 1}
    strata = sorted({g for s in cfgs.values() for g in (s["by_stratum"] or {})},
                    key=lambda g: (rank.get(g, 2), g))
    if not strata:
        return []
    few = [g for g in strata
           if any(cfgs[c]["by_stratum"][g].get("few_positives") for c in cfgs)]
    note = "Shows where the false positives fall."
    if few:
        note += (" Per-stratum sensitivity and PPV are omitted: "
                 + ", ".join(f"`{g}`" for g in few) + " has fewer than 5 gold positives.")
    header = ["config"]
    for g in strata:
        header += [f"`{g}` TP / FP / FN / TN", f"`{g}` specificity"]
    rows = []
    for c in order:
        row = [f"`{c}`"]
        for g in strata:
            m = cfgs[c]["by_stratum"][g]
            row += ["{tp} / {fp} / {fn} / {tn}".format(**m), fmt(m["specificity"])]
        rows.append(row)
    return ["## By stratum (primary rule)", "", note, ""] + _table(header, rows) + [""]


def extract_summary(md: str) -> str | None:
    """The hand-written block (markers included) from an existing results file, or None."""
    i, j = md.find(SUMMARY_START), md.find(SUMMARY_END)
    if i < 0 or j < i:
        return None
    return md[i:j + len(SUMMARY_END)]


def render(r: dict, summary: str | None = None) -> str:
    cfgs = r["configs"]
    order = _ordered(cfgs)
    n_pos = r["gold"].get("yes", 0)
    # With no gold `unclear` labels, the unclear rule and exclude_unclear are no-ops: omit them.
    has_unclear = r["gold"].get("unclear", 0) > 0
    variants = ("exclude_unclear", "strict") if has_unclear else ("strict",)
    L = [f"# Results: {r['set']} set", ""]
    if summary:
        L += [summary, ""]

    L += ["## Sample", "",
          f"- Notes: **{r['n']}**. Gold labels: {_gold_text(r['gold'], has_unclear)}."]
    for s, g in r["gold_by_stratum"].items():
        L.append(f"- `{s}`: {_gold_text(g, has_unclear)}.")
    L += ["- The sample is deliberately enriched for GOC, so these rates do **not** describe "
          "MIMIC-III as a whole.", ""]

    rule = f"Rule: {VARIANT_TEXT['primary']}. " if has_unclear else ""
    L += ["## Main results (primary rule)", "",
          f"{rule}Failed model calls count as `no`. "
          "Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.", ""]
    L += _table(
        ["config", "TP / FP / FN / TN", "sensitivity (recall)", "PPV (precision)",
         "specificity", "F1", "failures"],
        [[f"`{c}`", "{tp} / {fp} / {fn} / {tn}".format(**cfgs[c]["primary"]),
          fmt(cfgs[c]["primary"]["sensitivity"]), fmt(cfgs[c]["primary"]["ppv"]),
          fmt(cfgs[c]["primary"]["specificity"]), _f1(cfgs[c]["primary"]["f1"]),
          cfgs[c]["failures"]["n"]] for c in order])
    fails = {c: s["failures"]["by_type"] for c, s in cfgs.items() if s["failures"]["n"]}
    if fails:
        L += ["", "Failures by type: " + "; ".join(
            f"`{c}` " + ", ".join(f"{t} {len(ids)}" for t, ids in bt.items())
            for c, bt in fails.items()) + "."]
    L.append("")

    def breakdown(key: str, title: str) -> None:
        groups = sorted({g for s in cfgs.values() for g in (s[key] or {})})
        if not groups:
            return
        L.extend([f"## {title} (primary rule)", "",
                  "`*` = fewer than 5 gold positives in that group, so its sensitivity is "
                  "barely informative.", ""])
        rows = []
        for c in order:
            for g in groups:
                m = cfgs[c][key][g]
                star = " *" if m.get("few_positives") else ""
                rows.append([f"`{c}`", f"`{g}`{star}", "{tp} / {fp} / {fn} / {tn}".format(**m),
                             fmt(m["sensitivity"]), fmt(m["ppv"]), fmt(m["specificity"])])
        L.extend(_table(["config", "group", "TP / FP / FN / TN", "sensitivity (recall)",
                         "PPV (precision)", "specificity"], rows))
        L.append("")

    if r["set"] == "dev":
        L.extend(_compact_strata(cfgs, order))
    else:
        breakdown("by_stratum", "By stratum")
    breakdown("by_part", "By part")

    L += ["## Sensitivity analyses", ""]
    for v in variants:
        L += [f"- **{v}**: {VARIANT_TEXT[v]}."]
    L.append("")
    rows = []
    for c in order:
        row = [f"`{c}`", _f1(cfgs[c]["primary"]["f1"])]
        for v in variants:
            m = cfgs[c][v]
            row += [fmt(m["sensitivity"]), fmt(m["ppv"]), _f1(m["f1"])]
        rows.append(row)
    short = {"exclude_unclear": "excl.", "strict": "strict"}
    header = ["config", "F1 primary"]
    for v in variants:
        header += [f"sens/recall {short[v]}", f"PPV/precision {short[v]}", f"F1 {short[v]}"]
    L += _table(header, rows)
    L.append("")

    L += ["## Evidence spans", "",
          "Each quote the model gives is checked for an exact (whitespace-normalized, "
          "case-sensitive) match in the note. Shown as verified / given.", ""]
    L += _table(["config", "on `yes` answers", "on `no` answers"],
                [[f"`{c}`", "{verified} / {spans}".format(**cfgs[c]["spans"]["yes"]),
                  "{verified} / {spans}".format(**cfgs[c]["spans"]["no"])] for c in order])
    L.append("")

    mc = r["mcnemar"]
    if mc["pairs"]:
        tag = "exploratory, all pairs" if mc["exploratory"] else "pre-named pairs"
        L += [f"## Model comparisons (exact McNemar, Holm-adjusted; {tag})", "",
              "Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 "
              "should be called comparable.", ""]
        L += _table(["A", "B", "only A right", "only B right", "p", "Holm p", ""],
                    [[f"`{p['a']}`", f"`{p['b']}`", p["only_a_correct"], p["only_b_correct"],
                      _pval(p["p"]), _pval(p["p_holm"]),
                      "significant" if p["p_holm"] < 0.05 else "comparable"]
                     for p in mc["pairs"]])
        L.append("")

    L += ["## How to read this", "",
          "- **Sensitivity** (= recall): share of gold-`yes` notes the model called `yes`.",
          "- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.",
          "- **Specificity**: share of gold-`no` notes the model called `no`.",
          "- **F1**: harmonic mean of sensitivity and PPV (point estimate only).",
          "- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.",
          "- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for "
          "testing many pairs.",
          "- Accuracy is not reported. With mostly-`no` gold labels, a model that always says "
          "`no` would look accurate while finding nothing.",
          f"- Small sample: {r['n']} notes, {n_pos} gold positives. Intervals are wide and "
          "single-note changes move the point estimates a lot."]
    if r["set"] == "dev":
        L += ["- Dev labels come from 5 team members, one labeler per note, with no second "
              "opinion.",
              "- Dev is for prompt tuning and error inspection. It is not a reportable result."]
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_name", required=True, choices=list(PARTS))
    ap.add_argument("--reports", type=Path, default=REPORT_DIR)
    args = ap.parse_args()
    src = args.reports / f"eval_{args.set_name}.json"
    if not src.exists():
        print(f"missing {src.name}; run python -m src.eval.metrics --set {args.set_name} first")
        return 1
    out = args.reports / f"results_{args.set_name}.md"
    summary = extract_summary(out.read_text(encoding="utf-8")) if out.exists() else None
    out.write_text(render(json.loads(src.read_text(encoding="utf-8")), summary),
                   encoding="utf-8")
    print(f"wrote reports/{out.name}")
    if summary:
        print("kept the hand-written summary block; check it still matches the new numbers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
