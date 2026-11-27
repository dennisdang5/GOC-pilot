# Results: test_a set

## Sample

- Notes: **50**. Gold labels: yes 9 · no 41.
- `cues_missing`: yes 0 · no 15.
- `cues_present`: yes 9 · no 26.
- The sample is deliberately enriched for GOC, so these rates do **not** describe MIMIC-III as a whole.

## Main results (primary rule)

Failed model calls count as `no`. Proportions show the estimate and its 95% Wilson CI. Rows are sorted by F1.

| config | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | failures |
|---|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 8 / 11 / 1 / 30 | 0.89 (0.57-0.98) | 0.42 (0.23-0.64) | 0.73 (0.58-0.84) | 0.57 | 0 |

## By stratum (primary rule)

`*` = fewer than 5 gold positives in that group, so its sensitivity is barely informative.

| config | group | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity |
|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | `cues_missing` * | 0 / 0 / 0 / 15 | NA | NA | 1.00 (0.80-1.00) |
| `llama3.1-8b_zero_shot` | `cues_present` | 8 / 11 / 1 / 15 | 0.89 (0.57-0.98) | 0.42 (0.23-0.64) | 0.58 (0.39-0.74) |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given. **Grounded recall** is the share of gold-`yes` notes the model called `yes` with a verified quote (95% Wilson CI); a bad quote can only lower it.

| config | on `yes` answers | on `no` answers | grounded recall |
|---|---|---|---|
| `llama3.1-8b_zero_shot` | 15 / 19 | 0 / 0 | 0.67 (0.35-0.88) |

## How to read this

- **Sensitivity** (= recall): share of gold-`yes` notes the model called `yes`.
- **PPV** (precision): share of the model's `yes` calls that are gold `yes`.
- **Specificity**: share of gold-`no` notes the model called `no`.
- **F1**: harmonic mean of sensitivity and PPV (point estimate only).
- **Wilson CI**: a 95% interval for a proportion that behaves well with small counts.
- **McNemar**: tests whether two models differ on the same notes. Holm adjusts for testing many pairs.
- Accuracy is not reported. With mostly-`no` gold labels, a model that always says `no` would look accurate while finding nothing.
- Small sample: 50 notes, 9 gold positives. Intervals are wide and single-note changes move the point estimates a lot.
