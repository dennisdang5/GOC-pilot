# Results: dev set

<!-- summary:start -->
Run: 2026-10-29, CARC job 13535035 (A100).
<!-- summary:end -->

## Sample

- Notes: **30**. Gold labels: yes 8 · no 20 · unclear 2.
- `cues_missing`: yes 1 · no 8 · unclear 0.
- `cues_present`: yes 7 · no 12 · unclear 2.
- The sample is deliberately enriched for GOC, so these rates do **not** describe MIMIC-III as a whole.

## Main results (primary rule)

Rule: gold `unclear` counted as `no`. Failed model calls count as `no`. Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.

| config | TP / FP / FN / TN | sensitivity | PPV | specificity | F1 | failures |
|---|---|---|---|---|---|---|
| `qwen3-8b_few_shot` | 8 / 9 / 0 / 13 | 1.00 (0.68-1.00) | 0.47 (0.26-0.69) | 0.59 (0.39-0.77) | 0.64 | 0 |
| `llama3.1-8b_zero_shot` | 7 / 8 / 1 / 14 | 0.88 (0.53-0.98) | 0.47 (0.25-0.70) | 0.64 (0.43-0.80) | 0.61 | 0 |
| `qwen3-8b_zero_shot` | 8 / 12 / 0 / 10 | 1.00 (0.68-1.00) | 0.40 (0.22-0.61) | 0.45 (0.27-0.65) | 0.57 | 0 |
| `llama3.1-8b_few_shot` | 5 / 5 / 3 / 17 | 0.62 (0.31-0.86) | 0.50 (0.24-0.76) | 0.77 (0.57-0.90) | 0.56 | 0 |
| `gemma3-4b_zero_shot` | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 1 |
| `gemma3-4b_few_shot` | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0 |

Failures by type: `gemma3-4b_zero_shot` truncated 1.

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `qwen3-8b_few_shot` | 7 / 9 / 0 / 5 | 0.36 (0.16-0.61) | 1 / 0 / 0 / 8 | 1.00 (0.68-1.00) |
| `llama3.1-8b_zero_shot` | 6 / 8 / 1 / 6 | 0.43 (0.21-0.67) | 1 / 0 / 0 / 8 | 1.00 (0.68-1.00) |
| `qwen3-8b_zero_shot` | 7 / 11 / 0 / 3 | 0.21 (0.08-0.48) | 1 / 1 / 0 / 7 | 0.88 (0.53-0.98) |
| `llama3.1-8b_few_shot` | 5 / 5 / 2 / 9 | 0.64 (0.39-0.84) | 0 / 0 / 1 / 8 | 1.00 (0.68-1.00) |
| `gemma3-4b_zero_shot` | 7 / 14 / 0 / 0 | 0.00 (0.00-0.22) | 1 / 7 / 0 / 1 | 0.12 (0.02-0.47) |
| `gemma3-4b_few_shot` | 7 / 14 / 0 / 0 | 0.00 (0.00-0.22) | 1 / 8 / 0 / 0 | 0.00 (0.00-0.32) |

## Sensitivity analyses

- **exclude_unclear**: notes with gold `unclear` removed.
- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens excl. | PPV excl. | F1 excl. | sens strict | PPV strict | F1 strict |
|---|---|---|---|---|---|---|---|
| `qwen3-8b_few_shot` | 0.64 | 1.00 (0.68-1.00) | 0.53 (0.30-0.75) | 0.70 | 0.88 (0.53-0.98) | 0.47 (0.25-0.70) | 0.61 |
| `llama3.1-8b_zero_shot` | 0.61 | 0.88 (0.53-0.98) | 0.54 (0.29-0.77) | 0.67 | 0.62 (0.31-0.86) | 0.50 (0.24-0.76) | 0.56 |
| `qwen3-8b_zero_shot` | 0.57 | 1.00 (0.68-1.00) | 0.44 (0.25-0.66) | 0.62 | 0.75 (0.41-0.93) | 0.35 (0.17-0.59) | 0.48 |
| `llama3.1-8b_few_shot` | 0.56 | 0.62 (0.31-0.86) | 0.62 (0.31-0.86) | 0.62 | 0.50 (0.22-0.78) | 0.50 (0.22-0.78) | 0.50 |
| `gemma3-4b_zero_shot` | 0.43 | 1.00 (0.68-1.00) | 0.30 (0.16-0.48) | 0.46 | 0.50 (0.22-0.78) | 0.21 (0.09-0.43) | 0.30 |
| `gemma3-4b_few_shot` | 0.42 | 1.00 (0.68-1.00) | 0.29 (0.15-0.47) | 0.44 | 0.62 (0.31-0.86) | 0.50 (0.24-0.76) | 0.56 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `qwen3-8b_few_shot` | 15 / 17 | 0 / 0 |
| `llama3.1-8b_zero_shot` | 10 / 15 | 0 / 0 |
| `qwen3-8b_zero_shot` | 17 / 20 | 6 / 6 |
| `llama3.1-8b_few_shot` | 8 / 10 | 0 / 0 |
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

- **Sensitivity**: share of gold-`yes` notes the model called `yes`.
- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.
- **Specificity**: share of gold-`no` notes the model called `no`.
- **F1**: harmonic mean of sensitivity and PPV (point estimate only).
- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.
- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for testing many pairs.
- Accuracy is not reported. With mostly-`no` gold labels, a model that always says `no` would look accurate while finding nothing.
- Small sample: 30 notes, 8 gold positives. Intervals are wide and single-note changes move the point estimates a lot.
- Dev labels come from 5 team members, one labeler per note, with no second opinion.
- Dev is for prompt tuning and error inspection. It is not a reportable result.
