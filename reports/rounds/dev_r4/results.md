# Results: dev set, round r4

Round r4: run 2026-11-20, CARC job 14429508 (A100). Prompts: zero-shot `98dca2eeac05`, few-shot `8ebbfeef5e57`. Changes: r2 system/user prompt unchanged, with 5 new user-written synthetic few-shot examples (4 yes, 1 no; long palliative-style notes with [** **] placeholders) instead of the 4 r1 examples. num_ctx 16384 -> 32768 from r4 on, because the examples add ~12k tokens. Zero-shot prompt is identical to r2/r3 (same hash), so r2's zero-shot predictions are reused, not rerun.

<!-- summary:start -->
## Summary

*Hand-written for this round. Re-renders keep this block as-is, so check it against the
tables after a re-score. Numbers use the dev labels as revised on 2026-11-11 (8 yes · 22 no;
CLAUDE.md §3.6).*

### Findings

r4 keeps the r2 / r3 system and user prompts. It swaps the 4 r1 few-shot examples for 5 new
user-written synthetic ones (4 yes, 1 no; long palliative-style notes), and raises `num_ctx`
from 16384 to 32768. Those are **two changes at once**, so this round cannot separate their
effects. The zero-shot prompt is the same as in r2 and r3, so the zero-shot rows are r2's
predictions and show no change by construction.

1. **llama3.1 few-shot collapsed to all `no`.** It answered `no`, with no quote, on all 30
   notes: 0 of 8 positives found (r3: 6/8), F1 NA (r3: 0.75).
   - It is not a pipeline failure. All 30 calls succeeded with valid JSON and none was cut off.
     The prompts were 10.4k–14.0k tokens, well inside `num_ctx`. qwen3 and gemma3 received the
     same prompts and answered normally.
   - The replies were short (median latency 1.9 s in r3 → 1.3 s), consistent with an immediate
     `null` / `no`.
   - Example order does not explain it: the last example is a `yes`. Why the model responds this
     way cannot be determined from the aggregates.
2. **qwen3 few-shot lost recall.** It missed 3 positives that it found in r3 (sens 1.00 → 0.62)
   and its false positives stayed at 8 (1 fixed, 1 new): F1 0.67 → 0.48. Its quotes got
   better (12/13 verified on `yes`, against 12/16), but grounded recall stayed at 0.50.
3. **gemma3 few-shot is unchanged in practice.** It still says yes to almost everything (29/30;
   spec 0.09 → 0.05, F1 0.44 → 0.43). More of its quotes were verified (11/29, against 7/28).
   The `truncated` error on ROW_ID 561002 from r2 and r3 did not recur: with the larger context
   all 90 few-shot calls succeeded.
4. **No step from r3 to r4 is statistically significant** (all Holm p = 1.0; see
   [`rounds_dev.md`](../../rounds_dev.md)).
   - Even llama3.1 few-shot's collapse is only 6 notes worse against 2 better (p = 0.29).
   - Dev has 8 positives, so an all-`no` model loses only 8 notes and passes McNemar as
     "comparable". The test has little power on this set.
5. **llama3.1 zero-shot still leads on point estimates** (unchanged since r2): F1 0.84, all 8
   positives found, 3 false positives, grounded recall 0.75.
   - Its gaps to qwen3 few-shot and qwen3 zero-shot (8 vs 0 notes each) have Holm p = 0.086,
     so they remain formally tied. Every other 8b pair has Holm p = 1.0.
   - gemma3 zero-shot is below llama3.1 zero-shot (Holm p < 0.001) and qwen3 zero-shot
     (Holm p = 0.025). gemma3 few-shot is below llama3.1 zero-shot (Holm p < 0.001).
6. **False positives are still almost all in `cues_present`.** Each 8b config has at most 1 in
   `cues_missing`. All 8 gold positives are in `cues_present`, so recall in `cues_missing`
   cannot be measured on dev.

### Takeaways

- **The r4 examples are the weakest few-shot set so far for both 8b models.** They break
  llama3.1 and cost qwen3 3 positives, while gemma3 does not react. Don't freeze them.
- **The leading candidate is unchanged: llama3.1 zero-shot.** If a few-shot config also goes to
  test, r3's 4 examples are the better-supported choice for the 8b models (llama3.1 0.75,
  qwen3 0.67). Set `fewshot.jsonl` back to that version before `--freeze`.
- **Choose `num_ctx` before freezing.** Every zero-shot dev prediction since r2 ran at 16384,
  and the r3 few-shot predictions did too. The code now uses 32768. A test run at 32768 would
  use a setting those predictions were never made with. All test notes fit at 16384 under both
  strategies with the r2 / r3 prompts (§4.4), so 16384 would match what was scored on dev.
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
| `qwen3-8b_zero_shot` | 8 / 11 / 0 / 11 | 1.00 (0.68-1.00) | 0.42 (0.23-0.64) | 0.50 (0.31-0.69) | 0.59 | 0 |
| `qwen3-8b_few_shot` | 5 / 8 / 3 / 14 | 0.62 (0.31-0.86) | 0.38 (0.18-0.64) | 0.64 (0.43-0.80) | 0.48 | 0 |
| `gemma3-4b_few_shot` | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0 |
| `gemma3-4b_zero_shot` | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0 |
| `llama3.1-8b_few_shot` | 0 / 0 / 8 / 22 | 0.00 (0.00-0.32) | NA | 1.00 (0.85-1.00) | NA | 0 |

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 2 / 0 / 11 | 0.85 (0.58-0.96) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_few_shot` | 5 / 7 / 3 / 6 | 0.46 (0.23-0.71) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `gemma3-4b_few_shot` | 8 / 12 / 0 / 1 | 0.08 (0.01-0.33) | 0 / 9 / 0 / 0 | 0.00 (0.00-0.30) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 0 / 8 / 0 / 1 | 0.11 (0.02-0.43) |
| `llama3.1-8b_few_shot` | 0 / 0 / 8 / 13 | 1.00 (0.77-1.00) | 0 / 0 / 0 / 9 | 1.00 (0.70-1.00) |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given. **Grounded recall** is the share of gold-`yes` notes the model called `yes` with a verified quote (95% Wilson CI); a bad quote can only lower it.

| config | on `yes` answers | on `no` answers | grounded recall |
|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 11 | 0 / 0 | 0.75 (0.41-0.93) |
| `qwen3-8b_zero_shot` | 14 / 19 | 3 / 3 | 0.62 (0.31-0.86) |
| `qwen3-8b_few_shot` | 12 / 13 | 4 / 4 | 0.50 (0.22-0.78) |
| `gemma3-4b_few_shot` | 11 / 29 | 0 / 0 | 0.50 (0.22-0.78) |
| `gemma3-4b_zero_shot` | 15 / 29 | 1 / 1 | 0.62 (0.31-0.86) |
| `llama3.1-8b_few_shot` | 0 / 0 | 0 / 0 | 0.00 (0.00-0.32) |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

How the test works, in plain terms:

- It ignores notes that both models got right or both got wrong, and looks only at the notes where they disagree.
- If one model wins most of those notes, it is probably really better. If the split is close to even, the difference could just be luck.
- **p** is the chance of a split at least this lopsided if the two models were really equally good. Below 0.05 counts as a real difference.
- **Holm p** raises the bar, because we compare many pairs. The more tests you run, the more likely one passes by luck.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 1 | 1 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 8 | 21 | 0.024 | 0.191 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 0 | 18 | <0.001 | <0.001 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 3 | 13 | 0.021 | 0.191 | comparable |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 1 | 11 | 0.006 | 0.076 | comparable |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 8 | 21 | 0.024 | 0.191 | comparable |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 0 | 18 | <0.001 | <0.001 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 3 | 13 | 0.021 | 0.191 | comparable |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.025 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 3 | 8 | 0.227 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 8 | 5 | 0.581 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 11 | 8 | 0.648 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 8 | 0 | 0.008 | 0.086 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 8 | 0 | 0.008 | 0.086 | comparable |
| `qwen3-8b_few_shot` | `qwen3-8b_zero_shot` | 3 | 3 | 1.000 | 1.000 | comparable |

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
