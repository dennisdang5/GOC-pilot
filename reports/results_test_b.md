# Results: test_b set

## Sample

- Notes: **50**. Gold labels: yes 11 · no 39.
- `strong`: yes 11 · no 39.
- The sample is deliberately enriched for GOC, so these rates do **not** describe MIMIC-III as a whole.

## Main results (primary rule)

Failed model calls count as `no`. Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.

| config | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | failures |
|---|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 11 / 26 / 0 / 13 | 1.00 (0.74-1.00) | 0.30 (0.17-0.46) | 0.33 (0.21-0.49) | 0.46 | 1 |

Failures by type: `llama3.1-8b_zero_shot` truncated 1.

## By stratum (primary rule)

`*` = fewer than 5 gold positives in that group, so its sensitivity is barely informative.

| config | group | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity |
|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | `strong` | 11 / 26 / 0 / 13 | 1.00 (0.74-1.00) | 0.30 (0.17-0.46) | 0.33 (0.21-0.49) |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given. **Grounded recall** is the share of gold-`yes` notes the model called `yes` with a verified quote (95% Wilson CI); a bad quote can only lower it.

| config | on `yes` answers | on `no` answers | grounded recall |
|---|---|---|---|
| `llama3.1-8b_zero_shot` | 27 / 37 | 0 / 0 | 0.55 (0.28-0.79) |

## How to read this

- **Sensitivity** (= recall): share of gold-`yes` notes the model called `yes`.
- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.
- **Specificity**: share of gold-`no` notes the model called `no`.
- **F1**: harmonic mean of sensitivity and PPV (point estimate only).
- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.
- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for testing many pairs.
- Accuracy is not reported. With mostly-`no` gold labels, a model that always says `no` would look accurate while finding nothing.
- Small sample: 50 notes, 11 gold positives. Intervals are wide and single-note changes move the point estimates a lot.
