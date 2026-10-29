"""Score LLM predictions against the human gold labels for one set.

Run from the repo root:
  python -m src.eval.metrics --set dev [--labels ../GOC-labeler/labels]
  python -m src.eval.metrics --set combined --pair CONFIG_A CONFIG_B [--pair ...]

Sets: dev, test_a, test_b, combined (test_a + test_b, assembled here). Test sets are refused until
the prompts are frozen (src/llm/prompts/FROZEN), and their label files are not opened before then.

Rules (user-approved 2026-10-29):
- Gold "unclear" counts as "no" (primary). Variant exclude_unclear drops those notes.
- Failed predictions (parse / truncated) count as "no"; the failure count is reported per config.
- Variant strict: a "yes" without a verified evidence span counts as "no".
- Sensitivity, PPV and specificity with 95% Wilson CIs; F1 is a point estimate (not a proportion).
  Undefined metrics are None (printed NA), never 0.
- Per-stratum breakdowns; strata with fewer than 5 gold positives are flagged few_positives.
- Exact McNemar on correctness. Dev: all config pairs, Holm-adjusted, exploratory. Test sets:
  only the pairs named with --pair (named before the test run).

Writes reports/eval_{set}.json (aggregates) and reports/errors_{set}_{config}.csv (ROW_IDs of false
positives / negatives, gitignored via *.csv). Prints counts, metrics and ROW_IDs only.
Stratum comes from the sample parquets; src/sampling/ is never imported.
"""

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path

import pandas as pd
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

from src.labeling.collect import read_labels
from src.llm.notes import DERIVED, SAMPLES
from src.llm.prompts import STRATEGIES
from src.llm.run import check_frozen
from src.llm.validate import PRED_DIR, read_predictions

ROOT = Path(__file__).resolve().parents[2]
LABELS_DIR = ROOT.parent / "GOC-labeler" / "labels"
REPORT_DIR = ROOT / "reports"

ASSIGNMENTS = {"dev": [f"dev_{c}" for c in "ABCDE"], "test_a": ["test_physician"],
               "test_b": ["test_physician_b"]}
PARTS = {"dev": ["dev"], "test_a": ["test_a"], "test_b": ["test_b"],
         "combined": ["test_a", "test_b"]}
MIN_POSITIVES = 5


def wilson(k: int, n: int) -> dict | None:
    if n == 0:
        return None
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return {"k": k, "n": n, "est": k / n, "lo": float(lo), "hi": float(hi)}


def confusion(gold: pd.Series, pred: pd.Series) -> dict:
    return {"tp": int((gold & pred).sum()), "fp": int((~gold & pred).sum()),
            "fn": int((gold & ~pred).sum()), "tn": int((~gold & ~pred).sum())}


def scores(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    sens, ppv = wilson(tp, tp + fn), wilson(tp, tp + fp)
    f1 = (2 * tp / (2 * tp + fp + fn)) if sens and ppv and (tp + fp + fn) else None
    return {**c, "n": tp + fp + fn + tn, "positives": tp + fn, "sensitivity": sens, "ppv": ppv,
            "specificity": wilson(tn, tn + fp), "f1": f1}


# --- loading ---------------------------------------------------------------------------------

def load_gold(part: str, labels_dir: Path) -> dict[int, str]:
    """ROW_ID -> yes / no / unclear for one set. Opens only that set's label files."""
    names = set(ASSIGNMENTS[part])
    gold: dict[int, str] = {}
    for path in sorted(labels_dir.glob("*.jsonl")):
        if not any(path.name.startswith(f"{n}_") for n in names):
            continue
        latest, problems = read_labels(path)
        if problems:
            raise ValueError(f"{path.name}: {len(problems)} invalid lines (run src.labeling.collect)")
        for row_id, lab in latest.items():
            if lab.assignment not in names:
                continue
            if row_id in gold:
                raise ValueError(f"ROW_ID {row_id} labeled in more than one file")
            gold[row_id] = lab.goc_present
    return gold


def load_strata(part: str, derived: Path = DERIVED) -> dict[int, str]:
    df = pd.read_parquet(derived / SAMPLES[part], columns=["ROW_ID", "stratum"])
    return dict(zip(df["ROW_ID"].astype(int), df["stratum"]))


def load_configs(part: str, pred_dir: Path = PRED_DIR) -> dict[str, dict]:
    """config name (file stem minus set) -> {ROW_ID: Prediction}."""
    suffix = f"_{part}"
    return {p.stem[: -len(suffix)]: read_predictions(p)
            for p in sorted(pred_dir.glob(f"*{suffix}.jsonl"))}


def build_frame(set_name: str, labels_dir: Path, pred_dir: Path, derived: Path) -> pd.DataFrame:
    """One row per note: row_id, part, stratum, gold, and per config pred / verified / error."""
    frames, configs = [], {}
    for part in PARTS[set_name]:
        configs[part] = load_configs(part, pred_dir)
    if len({frozenset(c) for c in configs.values()}) > 1:
        raise ValueError(f"{set_name}: parts have different configs: "
                         f"{ {p: sorted(c) for p, c in configs.items()} }")
    for part in PARTS[set_name]:
        strata = load_strata(part, derived)
        gold = load_gold(part, labels_dir)
        missing = sorted(set(strata) - set(gold))
        if missing:
            raise ValueError(f"{part}: {len(missing)} notes have no gold label: {missing}")
        df = pd.DataFrame({"row_id": list(strata), "part": part,
                           "stratum": list(strata.values())})
        df["gold"] = df["row_id"].map(gold)
        for config, preds in configs[part].items():
            absent = sorted(set(strata) - set(preds))
            if absent:
                raise ValueError(f"{config} {part}: {len(absent)} notes without a prediction: "
                                 f"{absent}")
            df[f"{config}|answer"] = df["row_id"].map(lambda r: preds[r].goc_present)
            df[f"{config}|verified"] = df["row_id"].map(lambda r: preds[r].span_verified)
            df[f"{config}|error"] = df["row_id"].map(lambda r: preds[r].error)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def configs_in(df: pd.DataFrame) -> list[str]:
    return [c.split("|")[0] for c in df.columns if c.endswith("|answer")]


# --- scoring ---------------------------------------------------------------------------------

def predicted_yes(df: pd.DataFrame, config: str, strict: bool = False) -> pd.Series:
    yes = df[f"{config}|answer"].eq("yes")  # failures (None) count as no
    if strict:
        yes &= df[f"{config}|verified"].eq(True)
    return yes


def score_config(df: pd.DataFrame, config: str) -> dict:
    gold = df["gold"].eq("yes")
    pred = predicted_yes(df, config)
    keep = df["gold"].ne("unclear")
    by_stratum = {}
    for stratum, idx in df.groupby("stratum").groups.items():
        s = scores(confusion(gold[idx], pred[idx]))
        by_stratum[stratum] = {**s, "few_positives": s["positives"] < MIN_POSITIVES}
    errors = df[f"{config}|error"].dropna()
    answer, verified = df[f"{config}|answer"], df[f"{config}|verified"]
    spans = {a: {"spans": int(verified[answer.eq(a)].notna().sum()),
                 "verified": int(verified[answer.eq(a)].eq(True).sum())} for a in ("yes", "no")}
    return {
        "primary": scores(confusion(gold, pred)),
        "exclude_unclear": scores(confusion(gold[keep], pred[keep])),
        "strict": scores(confusion(gold, predicted_yes(df, config, strict=True))),
        "by_stratum": by_stratum,
        "by_part": {p: scores(confusion(gold[i], pred[i]))
                    for p, i in df.groupby("part").groups.items()} if df["part"].nunique() > 1
                   else None,
        "failures": {"n": int(len(errors)),
                     "by_type": {e: sorted(int(r) for r in df.loc[errors.index[errors == e],
                                                                   "row_id"])
                                 for e in errors.unique()}},
        "spans": spans,
        "false_positives": sorted(int(r) for r in df.loc[~gold & pred, "row_id"]),
        "false_negatives": sorted(int(r) for r in df.loc[gold & ~pred, "row_id"]),
    }


def mcnemar_pairs(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> list[dict]:
    """Exact McNemar on per-note correctness (primary rule), Holm-adjusted across pairs."""
    gold = df["gold"].eq("yes")
    rows = []
    for a, b in pairs:
        ok_a, ok_b = predicted_yes(df, a).eq(gold), predicted_yes(df, b).eq(gold)
        only_a, only_b = int((ok_a & ~ok_b).sum()), int((~ok_a & ok_b).sum())
        table = [[int((ok_a & ok_b).sum()), only_a], [only_b, int((~ok_a & ~ok_b).sum())]]
        p = float(mcnemar(table, exact=True).pvalue)
        rows.append({"a": a, "b": b, "only_a_correct": only_a, "only_b_correct": only_b, "p": p})
    if rows:
        adj = multipletests([r["p"] for r in rows], method="holm")[1]
        for r, q in zip(rows, adj):
            r["p_holm"] = float(q)
    return rows


def evaluate(set_name: str, df: pd.DataFrame, pairs: list[tuple[str, str]] | None) -> dict:
    configs = configs_in(df)
    if pairs is None:
        pairs = list(itertools.combinations(configs, 2)) if set_name == "dev" else []
    unknown = {c for p in pairs for c in p} - set(configs)
    if unknown:
        raise ValueError(f"unknown configs in --pair: {sorted(unknown)}")
    return {
        "set": set_name,
        "n": int(len(df)),
        "gold": {k: int(v) for k, v in df["gold"].value_counts().items()},
        "gold_by_stratum": {s: {k: int(v) for k, v in g["gold"].value_counts().items()}
                            for s, g in df.groupby("stratum")},
        "configs": {c: score_config(df, c) for c in configs},
        "mcnemar": {"exploratory": set_name == "dev", "pairs": mcnemar_pairs(df, pairs)},
    }


# --- output ----------------------------------------------------------------------------------

def fmt(p: dict | None) -> str:
    return "NA" if p is None else f"{p['est']:.2f} ({p['lo']:.2f}-{p['hi']:.2f})"


def print_report(r: dict) -> None:
    print(f"set {r['set']}: n={r['n']}  gold {r['gold']}  by stratum {r['gold_by_stratum']}")
    head = f"{'config':<26}{'fail':>5}{'TP':>4}{'FP':>4}{'FN':>4}{'TN':>4}  " \
           f"{'sensitivity':<18}{'PPV':<18}{'specificity':<18}{'F1':>5}"
    for variant in ("primary", "exclude_unclear", "strict"):
        print(f"\n[{variant}]\n{head}")
        for c, s in r["configs"].items():
            m = s[variant]
            f1 = "NA" if m["f1"] is None else f"{m['f1']:.2f}"
            print(f"{c:<26}{s['failures']['n']:>5}{m['tp']:>4}{m['fp']:>4}{m['fn']:>4}{m['tn']:>4}"
                  f"  {fmt(m['sensitivity']):<18}{fmt(m['ppv']):<18}{fmt(m['specificity']):<18}"
                  f"{f1:>5}")
    print("\n[by stratum, primary]  TP/FP/FN/TN  sensitivity  specificity  (* = <5 positives)")
    for c, s in r["configs"].items():
        cells = [f"{k} {m['tp']}/{m['fp']}/{m['fn']}/{m['tn']} {fmt(m['sensitivity'])} "
                 f"{fmt(m['specificity'])}{' *' if m['few_positives'] else ''}"
                 for k, m in s["by_stratum"].items()]
        print(f"{c:<26}" + " | ".join(cells))
    print("\n[spans]  on yes: verified/given   on no: verified/given   failures")
    for c, s in r["configs"].items():
        y, n = s["spans"]["yes"], s["spans"]["no"]
        print(f"{c:<26}{y['verified']:>3}/{y['spans']:<3}  {n['verified']:>10}/{n['spans']:<3}"
              f"  {s['failures']['by_type'] or '-'}")
    mc = r["mcnemar"]
    if mc["pairs"]:
        tag = "exploratory, " if mc["exploratory"] else ""
        print(f"\n[McNemar exact, {tag}Holm]  only-a / only-b correct")
        for p in mc["pairs"]:
            print(f"{p['a']} vs {p['b']}: {p['only_a_correct']}/{p['only_b_correct']}  "
                  f"p={p['p']:.3f}  p_holm={p['p_holm']:.3f}")


def write_outputs(r: dict, report_dir: Path = REPORT_DIR) -> None:
    report_dir.mkdir(exist_ok=True)
    (report_dir / f"eval_{r['set']}.json").write_text(json.dumps(r, indent=2) + "\n",
                                                      encoding="utf-8")
    for c, s in r["configs"].items():
        with (report_dir / f"errors_{r['set']}_{c}.csv").open("w", newline="",
                                                             encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ROW_ID", "error"])
            w.writerows([(i, "FP") for i in s["false_positives"]] +
                        [(i, "FN") for i in s["false_negatives"]])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="set_name", required=True, choices=list(PARTS))
    ap.add_argument("--labels", type=Path, default=LABELS_DIR)
    ap.add_argument("--pair", nargs=2, action="append", metavar=("CONFIG_A", "CONFIG_B"))
    args = ap.parse_args()
    try:
        for part in PARTS[args.set_name]:
            for strategy in STRATEGIES:
                check_frozen(part, strategy)
    except PermissionError as e:
        print(f"refused: {e}")
        return 1
    try:
        df = build_frame(args.set_name, args.labels, PRED_DIR, DERIVED)
        report = evaluate(args.set_name, df, [tuple(p) for p in args.pair] if args.pair else None)
    except ValueError as e:  # messages hold counts, ROW_IDs and config names only
        print(f"eval: {e}")
        return 1
    print_report(report)
    write_outputs(report)
    print(f"\nwrote reports/eval_{args.set_name}.json and reports/errors_{args.set_name}_*.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
