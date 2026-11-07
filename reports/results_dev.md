# Results: dev set

<!-- summary:start -->
Run: 2026-10-29, CARC job 13535035 (A100).

## Summary

*Hand-written for the run above. Re-renders keep this block as-is, so check it against the
tables after a new run.*

### Findings

1. **Recall is high; precision is the problem.** Four of the six configs find all 9 gold-yes
   notes (recall 1.00), but even the best configs are right only about half the time when they
   say yes (PPV 0.45–0.60 for the 8b configs).
2. **The 8b configs are statistically tied.** qwen3 few-shot has the highest F1 (0.69: recall
   1.00, PPV 0.53), with llama3.1 zero-shot next (0.67). McNemar finds no difference between any
   two of the four 8b configs (all Holm p = 1.0).
3. **gemma3:4b says yes to almost everything** (specificity 0.05 zero-shot, 0.00 few-shot).
   Every 8b config beats it (Holm p 0.004–0.035), the only statistically clear result.
4. **Whether few-shot helps depends on the model.** For qwen3, the examples cut false positives
   from 11 to 8 at the same recall. For llama3.1, false positives fell from 7 to 4 but misses
   rose from 1 to 3 (recall 0.89 → 0.67). Neither change is significant.
5. **False positives are concentrated in notes with GOC vocabulary.** Nearly all of them are in
   `cues_present` (all 8 of qwen3 few-shot's). In `cues_missing`, the 8b configs have 0–1 false
   positives.
6. **The 8b models' quotes are mostly real** (67–88% verified on yes answers, against 33–66% for
   gemma3). The strict rule costs each 8b config 1–3 true positives: qwen3 few-shot loses 1
   (F1 0.69 → 0.67), and llama3.1 zero-shot loses 3 (F1 0.67 → 0.53).
7. **The runs were reliable.** 179 of 180 calls succeeded (1 gemma3 output-length truncation).

### Takeaways

- **Tune for precision, not recall.** The models already find the GOC notes. The prompt has to
  stop them from saying yes when GOC words appear without a documented conversation with the
  patient or family, for example "palliative care consulted", "will hold family meeting
  tomorrow", or clinicians talking among themselves.
- **Treat these numbers as directional.** With 9 positives, one note moves recall by about
  0.11. Reportable results come only from the frozen test sets.
<!-- summary:end -->

## Sample

- Notes: **30**. Gold labels: yes 9 · no 21.
- `cues_missing`: yes 1 · no 8.
- `cues_present`: yes 8 · no 13.
- The sample is deliberately enriched for GOC, so these rates do **not** describe MIMIC-III as a whole.

## Main results (primary rule)

Failed model calls count as `no`. Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.

| config | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | failures |
|---|---|---|---|---|---|---|
| `qwen3-8b_few_shot` | 9 / 8 / 0 / 13 | 1.00 (0.70-1.00) | 0.53 (0.31-0.74) | 0.62 (0.41-0.79) | 0.69 | 0 |
| `llama3.1-8b_zero_shot` | 8 / 7 / 1 / 14 | 0.89 (0.57-0.98) | 0.53 (0.30-0.75) | 0.67 (0.45-0.83) | 0.67 | 0 |
| `llama3.1-8b_few_shot` | 6 / 4 / 3 / 17 | 0.67 (0.35-0.88) | 0.60 (0.31-0.83) | 0.81 (0.60-0.92) | 0.63 | 0 |
| `qwen3-8b_zero_shot` | 9 / 11 / 0 / 10 | 1.00 (0.70-1.00) | 0.45 (0.26-0.66) | 0.48 (0.28-0.68) | 0.62 | 0 |
| `gemma3-4b_zero_shot` | 9 / 20 / 0 / 1 | 1.00 (0.70-1.00) | 0.31 (0.17-0.49) | 0.05 (0.01-0.23) | 0.47 | 1 |
| `gemma3-4b_few_shot` | 9 / 21 / 0 / 0 | 1.00 (0.70-1.00) | 0.30 (0.17-0.48) | 0.00 (0.00-0.15) | 0.46 | 0 |

Failures by type: `gemma3-4b_zero_shot` truncated 1.

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `qwen3-8b_few_shot` | 8 / 8 / 0 / 5 | 0.38 (0.18-0.64) | 1 / 0 / 0 / 8 | 1.00 (0.68-1.00) |
| `llama3.1-8b_zero_shot` | 7 / 7 / 1 / 6 | 0.46 (0.23-0.71) | 1 / 0 / 0 / 8 | 1.00 (0.68-1.00) |
| `llama3.1-8b_few_shot` | 6 / 4 / 2 / 9 | 0.69 (0.42-0.87) | 0 / 0 / 1 / 8 | 1.00 (0.68-1.00) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 1 / 1 / 0 / 7 | 0.88 (0.53-0.98) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 1 / 7 / 0 / 1 | 0.12 (0.02-0.47) |
| `gemma3-4b_few_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 1 / 8 / 0 / 0 | 0.00 (0.00-0.32) |

## Sensitivity analyses

- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens/recall strict | PPV/precision strict | F1 strict |
|---|---|---|---|---|
| `qwen3-8b_few_shot` | 0.69 | 0.89 (0.57-0.98) | 0.53 (0.30-0.75) | 0.67 |
| `llama3.1-8b_zero_shot` | 0.67 | 0.56 (0.27-0.81) | 0.50 (0.24-0.76) | 0.53 |
| `llama3.1-8b_few_shot` | 0.63 | 0.44 (0.19-0.73) | 0.50 (0.22-0.78) | 0.47 |
| `qwen3-8b_zero_shot` | 0.62 | 0.78 (0.45-0.94) | 0.41 (0.22-0.64) | 0.54 |
| `gemma3-4b_zero_shot` | 0.47 | 0.44 (0.19-0.73) | 0.21 (0.09-0.43) | 0.29 |
| `gemma3-4b_few_shot` | 0.46 | 0.56 (0.27-0.81) | 0.50 (0.24-0.76) | 0.53 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `qwen3-8b_few_shot` | 15 / 17 | 0 / 0 |
| `llama3.1-8b_zero_shot` | 10 / 15 | 0 / 0 |
| `llama3.1-8b_few_shot` | 8 / 10 | 0 / 0 |
| `qwen3-8b_zero_shot` | 17 / 20 | 6 / 6 |
| `gemma3-4b_zero_shot` | 19 / 29 | 0 / 0 |
| `gemma3-4b_few_shot` | 10 / 30 | 0 / 0 |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 0 | 1 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 3 | 17 | 0.003 | 0.026 | significant |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 1 | 14 | <0.001 | 0.013 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 0 | 13 | <0.001 | 0.004 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.022 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 3 | 16 | 0.004 | 0.035 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 1 | 13 | 0.002 | 0.022 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 0 | 12 | <0.001 | 0.007 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 9 | 0.004 | 0.035 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 3 | 2 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 4 | 3 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 7 | 3 | 0.344 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 1 | 1 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 4 | 1 | 0.375 | 1.000 | comparable |
| `qwen3-8b_few_shot` | `qwen3-8b_zero_shot` | 3 | 0 | 0.250 | 1.000 | comparable |

## How to read this

- **Sensitivity** (= recall): share of gold-`yes` notes the model called `yes`.
- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.
- **Specificity**: share of gold-`no` notes the model called `no`.
- **F1**: harmonic mean of sensitivity and PPV (point estimate only).
- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.
- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for testing many pairs.
- Accuracy is not reported. With mostly-`no` gold labels, a model that always says `no` would look accurate while finding nothing.
- Small sample: 30 notes, 9 gold positives. Intervals are wide and single-note changes move the point estimates a lot.
- Dev labels come from 5 team members, one labeler per note, with no second opinion.
- Dev is for prompt tuning and error inspection. It is not a reportable result.
