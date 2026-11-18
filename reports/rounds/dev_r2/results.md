# Results: dev set, round r2

Round r2: run 2026-11-11, CARC job 14030227 (A100). Prompts: zero-shot `98dca2eeac05`, few-shot `70187780106a`. Changes: User-written system prompt: two tests, (A) a conversation with the patient/family/HCP already happened, or they made an overall-direction decision (CMO, withdrawal, hospice, stop chemo), and (B) it has content (goals, values, prognosis shared, or a treatment preference/decision); 9 always-no patterns (code status, empty templates, planned talks, updates, team plans/consults, content-free meetings, medical management, comfort orders, stated preferences + referral), 3 yes patterns, a 4-step procedure; evidence_span must pass A and B. Few-shot: 16 synthetic examples (6 yes, 10 no), replacing the 4. num_ctx 12288 -> 16384 from r2 on, so every test note fits under few-shot.

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
  than under the primary rule (gemma3 few-shot here: 0.60 strict against 0.56 primary; in r0 it
  was 0.56 against 0.42). Read strict F1 together with the quotes-verified counts, not on its
  own.

### Findings

1. **Only gemma3 few-shot changed significantly.** With the 16 synthetic examples it stopped
   saying yes to everything: 12 fewer false positives and 1 new miss (McNemar 1 vs 12 notes,
   Holm p = 0.021). Its specificity went from 0.00 to 0.55. Every other config is
   "comparable" to r1 (Holm p = 1.0). See [`rounds_dev.md`](../../rounds_dev.md).
2. **llama3.1 zero-shot now leads on point estimates.** It found all 8 positives with 3 false
   positives: F1 0.84 (recall 1.00, PPV 0.73, specificity 0.86), up from 0.70 in r1 and 0.61
   in r0. It also has the best strict F1 (0.75).
3. **llama3.1 few-shot went back to its r0 level.** It gained 3 false positives and still misses
   2 positives: F1 0.80 → 0.67 (not significant, 5 vs 2 notes). The long few-shot prompt helped
   gemma3 but not llama3.1.
4. **qwen3 barely moved.** Few-shot gives the same counts as r1 (8 FP, F1 0.67); zero-shot lost
   1 false positive (11 FP, F1 0.59). Both still find all 8 positives.
5. **The 8b configs are still statistically tied.** The largest gap, llama3.1 zero-shot vs qwen3
   zero-shot (8 vs 0 notes), has p = 0.008 unadjusted but Holm p = 0.078. Every other 8b pair
   has Holm p ≥ 0.50. gemma3 zero-shot (yes on 29/30 notes) is below every 8b config (Holm p
   ≤ 0.023); gemma3 few-shot is not significantly different from any of them (Holm p ≥ 0.078).
6. **Recall held.** Every 8b config has recall ≥ 0.75, and three of the four have 1.00. The only
   new miss across all configs is gemma3 few-shot's.
7. **False positives are still almost all in `cues_present`.** Each 8b config now has 1 false
   positive in `cues_missing` (llama3.1 had none in r1). All 8 gold positives sit in
   `cues_present`, so recall in `cues_missing` cannot be measured on dev.
8. **Quotes are 70–82% verified on yes answers** for all configs except gemma3 zero-shot (15/29).
   llama3.1's verification recovered a little (zero-shot 7/12 → 8/11, few-shot 5/7 → 7/10). qwen3
   zero-shot gave 3 quotes with a `no` answer.
9. **The run was reliable.** 179 of 180 calls succeeded. gemma3 few-shot hit the output limit
   on 1 note (`truncated`, scored as `no`; that note is gold `no`).

### Takeaways

- **Freezing after r2 is reasonable.** No step since r0 is significant for any 8b config, and
  with 8 positives another round would mostly fit noise in the 30 dev notes.
- **Expect llama3.1 zero-shot to be the leading candidate on test, but not a proven winner.**
  Its dev lead over the other 8b configs is not significant. Dev is also optimistic for it: the
  prompts were tuned on these notes, and labels were revised after seeing model output.
- **Watch false positives and quotes on test.** False positives were the main error in every
  round. Test_b is enriched for positives, so recall there will likely look better than on
  less explicit notes.
- **Treat these numbers as directional.** With 8 positives, one note moves recall by about
  0.12. Reportable results come only from the frozen test sets.
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
| `llama3.1-8b_few_shot` | 6 / 4 / 2 / 18 | 0.75 (0.41-0.93) | 0.60 (0.31-0.83) | 0.82 (0.61-0.93) | 0.67 | 0 |
| `qwen3-8b_few_shot` | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0 |
| `qwen3-8b_zero_shot` | 8 / 11 / 0 / 11 | 1.00 (0.68-1.00) | 0.42 (0.23-0.64) | 0.50 (0.31-0.69) | 0.59 | 0 |
| `gemma3-4b_few_shot` | 7 / 10 / 1 / 12 | 0.88 (0.53-0.98) | 0.41 (0.22-0.64) | 0.55 (0.35-0.73) | 0.56 | 1 |
| `gemma3-4b_zero_shot` | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0 |

Failures by type: `gemma3-4b_few_shot` truncated 1.

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 2 / 0 / 11 | 0.85 (0.58-0.96) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `llama3.1-8b_few_shot` | 6 / 3 / 2 / 10 | 0.77 (0.50-0.92) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_few_shot` | 8 / 7 / 0 / 6 | 0.46 (0.23-0.71) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `gemma3-4b_few_shot` | 7 / 9 / 1 / 4 | 0.31 (0.13-0.58) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 0 / 8 / 0 / 1 | 0.11 (0.02-0.43) |

## Sensitivity analyses

- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens/recall strict | PPV/precision strict | F1 strict |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 0.84 | 0.75 (0.41-0.93) | 0.75 (0.41-0.93) | 0.75 |
| `llama3.1-8b_few_shot` | 0.67 | 0.50 (0.22-0.78) | 0.57 (0.25-0.84) | 0.53 |
| `qwen3-8b_few_shot` | 0.67 | 0.75 (0.41-0.93) | 0.46 (0.23-0.71) | 0.57 |
| `qwen3-8b_zero_shot` | 0.59 | 0.62 (0.31-0.86) | 0.36 (0.16-0.61) | 0.45 |
| `gemma3-4b_few_shot` | 0.56 | 0.75 (0.41-0.93) | 0.50 (0.25-0.75) | 0.60 |
| `gemma3-4b_zero_shot` | 0.43 | 0.62 (0.31-0.86) | 0.33 (0.15-0.58) | 0.43 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 11 | 0 / 0 |
| `llama3.1-8b_few_shot` | 7 / 10 | 0 / 0 |
| `qwen3-8b_few_shot` | 13 / 16 | 1 / 1 |
| `qwen3-8b_zero_shot` | 14 / 19 | 3 / 3 |
| `gemma3-4b_few_shot` | 12 / 15 | 0 / 0 |
| `gemma3-4b_zero_shot` | 15 / 29 | 1 / 1 |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 11 | 1 | 0.006 | 0.070 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 1 | 6 | 0.125 | 0.875 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 0 | 8 | 0.008 | 0.078 | comparable |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 1 | 4 | 0.375 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 3 | 3 | 1.000 | 1.000 | comparable |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 2 | 17 | <0.001 | 0.009 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 0 | 18 | <0.001 | <0.001 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 0 | 13 | <0.001 | 0.003 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.023 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 1 | 4 | 0.375 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 4 | 2 | 0.688 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 7 | 2 | 0.180 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 5 | 0 | 0.062 | 0.500 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 8 | 0 | 0.008 | 0.078 | comparable |
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
