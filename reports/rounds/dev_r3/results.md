# Results: dev set, round r3

Round r3: run 2026-11-19, CARC job 14366175 (A100). Prompts: zero-shot `98dca2eeac05`, few-shot `152a46a1e633`. Changes: r2 system/user prompt unchanged, with the 4 r1 few-shot examples instead of the 16 r2 examples (tests whether the 16 examples hurt few-shot). Zero-shot prompt is identical to r2 (same hash), so r2's zero-shot predictions are reused, not rerun.

<!-- summary:start -->
## Summary

*Hand-written for this round. Re-renders keep this block as-is, so check it against the
tables after a re-score. Numbers use the dev labels as revised on 2026-11-11 (8 yes · 22 no;
CLAUDE.md §3.6).*

### About F1 strict

F1 strict is a stricter scoring of the same predictions. A model `yes` counts only if its quote
(`evidence_span`) can be found word for word in the note.

- **How it is calculated.**
  - Each `yes` answer's quote is checked against the note. The match must be exact and
    case-sensitive, with runs of whitespace treated as a single space.
  - A `yes` whose quote is missing or not found is recounted as `no`. `no` answers are
    unchanged.
  - TP / FP / FN / TN, sensitivity, PPV and F1 are then recomputed in the usual way.
- **Why it is reported.** It shows how well a model does when every `yes` must come with
  evidence a reader can check. That matters for silver labeling, where most notes are never read
  in full.
- **How to read it.** The rule can only turn `yes` into `no`, so a wrong `yes` with a bad quote
  becomes a correct `no`. A model with poor quotes can therefore score *higher* under strict
  than under the primary rule. gemma3 few-shot is the clearest case this round: 0.67 strict
  against 0.44 primary, because only 7 of its 28 quotes were verified. Read strict F1 together
  with the quotes-verified counts, not on its own.

### Findings

r3 changes only the few-shot examples (the 4 r1 examples in place of the 16 r2 examples). The
zero-shot prompt is the same as r2, so the zero-shot rows are r2's predictions and show no
change by construction.

1. **No few-shot config changed significantly from r2.** Every r2 → r3 step is "comparable"
   (Holm p ≥ 0.070). See [`rounds_dev.md`](../../rounds_dev.md).
2. **llama3.1 few-shot recovered partly.** 3 notes were fixed and 1 new false positive was
   added (McNemar 1 vs 3, p = 0.63). The net effect is 2 fewer false positives: F1 0.67 → 0.75
   (sens 0.75, PPV 0.75, spec 0.91). That is still below its r1 score (0.80), and it still
   misses the same 2 positives as in r0–r2. Its strict F1 rose 0.53 → 0.71 (6/8 quotes
   verified).
3. **qwen3 few-shot gave exactly the same answer on all 30 notes** as in r2 (8 FP, F1 0.67).
   Only its quotes changed: 12/16 verified (13/16 in r2), and strict F1 fell 0.57 → 0.40.
4. **gemma3 few-shot lost its r2 gain.** With 4 examples it went back to saying yes to almost
   everything: 10 more false positives and 1 fewer miss (McNemar 10 vs 1, p = 0.012, Holm
   p = 0.070). Specificity fell 0.55 → 0.09. The 16 examples were what helped gemma3 in r2.
   It again hit the output limit on ROW_ID 561002 (`truncated`, scored as `no`; gold `no`), the
   same note as in r2.
5. **llama3.1 zero-shot still leads on point estimates** (unchanged from r2): F1 0.84, all 8
   positives found, 3 false positives, strict F1 0.75. llama3.1 few-shot is now second (0.75).
   The two llama3.1 configs disagree on only 5 notes (2 vs 3, p = 1.0).
6. **The 8b configs are still statistically tied.** The largest gap, llama3.1 zero-shot vs qwen3
   zero-shot (8 vs 0 notes), has Holm p = 0.062. Every other 8b pair has Holm p ≥ 0.375.
   gemma3 zero-shot is below every 8b config (Holm p ≤ 0.018); gemma3 few-shot is below every
   8b config except qwen3 zero-shot (Holm p = 0.082).
7. **False positives are still almost all in `cues_present`.** llama3.1 few-shot has none in
   `cues_missing`; the other 8b configs have 1 each. All 8 gold positives are in
   `cues_present`, so recall in `cues_missing` cannot be measured on dev.
8. **The run was reliable.** All 90 new few-shot calls ran; 89 succeeded and 1 was `truncated`
   (gemma3, above). The 90 zero-shot notes were skipped as planned.

### Takeaways

- **The 16 r2 examples did not cause llama3.1 few-shot's r2 drop in any measurable way.**
  Switching back to the 4 r1 examples moved it by a net of 2 notes, which is within noise.
  qwen3 did not react at all, and gemma3 needs the longer set to avoid saying yes to everything.
- **The leading candidate is unchanged: llama3.1 zero-shot.** Its prompt is the same in r2 and
  r3, so the choice of few-shot file only matters if a few-shot config goes to test. If one
  does, r3's 4 examples suit llama3.1 slightly better (point estimates only) and r2's 16 suit
  gemma3; qwen3 is indifferent.
- **Freezing now is reasonable.** No step since r0 is significant for any 8b config, and another
  round would mostly fit noise in 30 notes with 8 positives. Set `fewshot.jsonl` to the chosen
  round's version before `--freeze`.
- **Treat these numbers as directional.** One note moves recall by about 0.12, the prompts were
  tuned on these notes, and labels were revised after seeing model output. Reportable results
  come only from the frozen test sets.
<!-- summary:end -->

## Sample

- Notes: **30**. Gold labels: yes 8 · no 22.
- `cues_missing`: yes 0 · no 9.
- `cues_present`: yes 8 · no 13.
- The sample is deliberately enriched for GOC, so these rates do **not** describe MIMIC-III as a whole.

## Main results (primary rule)

Failed model calls count as `no`. Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.

| config | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | failures |
|---|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 3 / 0 / 19 | 1.00 (0.68-1.00) | 0.73 (0.43-0.90) | 0.86 (0.67-0.95) | 0.84 | 0 |
| `llama3.1-8b_few_shot` | 6 / 2 / 2 / 20 | 0.75 (0.41-0.93) | 0.75 (0.41-0.93) | 0.91 (0.72-0.97) | 0.75 | 0 |
| `qwen3-8b_few_shot` | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0 |
| `qwen3-8b_zero_shot` | 8 / 11 / 0 / 11 | 1.00 (0.68-1.00) | 0.42 (0.23-0.64) | 0.50 (0.31-0.69) | 0.59 | 0 |
| `gemma3-4b_few_shot` | 8 / 20 / 0 / 2 | 1.00 (0.68-1.00) | 0.29 (0.15-0.47) | 0.09 (0.03-0.28) | 0.44 | 1 |
| `gemma3-4b_zero_shot` | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0 |

Failures by type: `gemma3-4b_few_shot` truncated 1.

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 2 / 0 / 11 | 0.85 (0.58-0.96) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `llama3.1-8b_few_shot` | 6 / 2 / 2 / 11 | 0.85 (0.58-0.96) | 0 / 0 / 0 / 9 | 1.00 (0.70-1.00) |
| `qwen3-8b_few_shot` | 8 / 7 / 0 / 6 | 0.46 (0.23-0.71) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `gemma3-4b_few_shot` | 8 / 12 / 0 / 1 | 0.08 (0.01-0.33) | 0 / 8 / 0 / 1 | 0.11 (0.02-0.43) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 0 / 8 / 0 / 1 | 0.11 (0.02-0.43) |

## Sensitivity analyses

- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens/recall strict | PPV/precision strict | F1 strict |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 0.84 | 0.75 (0.41-0.93) | 0.75 (0.41-0.93) | 0.75 |
| `llama3.1-8b_few_shot` | 0.75 | 0.62 (0.31-0.86) | 0.83 (0.44-0.97) | 0.71 |
| `qwen3-8b_few_shot` | 0.67 | 0.50 (0.22-0.78) | 0.33 (0.14-0.61) | 0.40 |
| `qwen3-8b_zero_shot` | 0.59 | 0.62 (0.31-0.86) | 0.36 (0.16-0.61) | 0.45 |
| `gemma3-4b_few_shot` | 0.44 | 0.62 (0.31-0.86) | 0.71 (0.36-0.92) | 0.67 |
| `gemma3-4b_zero_shot` | 0.43 | 0.62 (0.31-0.86) | 0.33 (0.15-0.58) | 0.43 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 11 | 0 / 0 |
| `llama3.1-8b_few_shot` | 6 / 8 | 0 / 0 |
| `qwen3-8b_few_shot` | 12 / 16 | 1 / 1 |
| `qwen3-8b_zero_shot` | 14 / 19 | 3 / 3 |
| `gemma3-4b_few_shot` | 7 / 28 | 0 / 0 |
| `gemma3-4b_zero_shot` | 15 / 29 | 1 / 1 |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 1 | 0 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 2 | 18 | <0.001 | 0.004 | significant |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 0 | 17 | <0.001 | <0.001 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 1 | 13 | 0.002 | 0.018 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 1 | 10 | 0.012 | 0.082 | comparable |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 2 | 19 | <0.001 | 0.003 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 0 | 18 | <0.001 | <0.001 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 0 | 13 | <0.001 | 0.003 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.018 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 2 | 3 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 6 | 2 | 0.289 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 9 | 2 | 0.065 | 0.375 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 5 | 0 | 0.062 | 0.375 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 8 | 0 | 0.008 | 0.062 | comparable |
| `qwen3-8b_few_shot` | `qwen3-8b_zero_shot` | 3 | 0 | 0.250 | 1.000 | comparable |

## How to read this

- **Sensitivity** (= recall): share of gold-`yes` notes the model called `yes`.
- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.
- **Specificity**: share of gold-`no` notes the model called `no`.
- **F1**: harmonic mean of sensitivity and PPV (point estimate only).
- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.
- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for testing many pairs.
- Accuracy is not reported. With mostly-`no` gold labels, a model that always says `no` would look accurate while finding nothing.
- Small sample: 30 notes, 8 gold positives. Intervals are wide and single-note changes move the point estimates a lot.
- Dev labels come from 5 team members, one labeler per note, with no second opinion.
- Dev is for prompt tuning and error inspection. It is not a reportable result.
