# Results: dev set, round r1

Round r1: run 2026-11-09, CARC job 13933520 (A100). Prompts: zero-shot `84e5a005cefb`, few-shot `eea596c7e013`. Changes: From dev triage (CMO status lines; planned meeting + family update): CMO / comfort orders join the code-status rule; planned meeting with a family update -> no, real conversation + follow-up -> yes; must find the sentence describing the conversation, and evidence_span must be that sentence; 4th few-shot example (hard no: CMO + update + planned meeting).

<!-- summary:start -->
## Summary

*Hand-written for this round. Re-renders keep this block as-is, so check it against the
tables after a re-score.*

### Findings

1. **Round 1 did not measurably change any config.** McNemar finds no r0 → r1 difference for
   any of the six configs (all Holm p = 1.0). At most 3 notes changed correctness per config.
   See [`rounds_dev.md`](../../rounds_dev.md).
2. **llama3.1 became more conservative in both strategies.** It has 2 fewer false positives
   and 1 more miss in each. Zero-shot F1 is unchanged at 0.67 (PPV 0.53 → 0.58, recall
   0.89 → 0.78). Few-shot reaches the highest specificity so far (0.90), but recall falls to
   0.56 (F1 0.63 → 0.62).
3. **qwen3 hardly responded.** Its false positives did not move (few-shot 8, zero-shot 11).
   Few-shot lost one true positive (recall 1.00 → 0.89, F1 0.69 → 0.64). Zero-shot gives the
   same answer as r0 on every note.
4. **The 8b configs are still statistically tied.** llama3.1 zero-shot now has the highest F1
   (0.67), followed by qwen3 few-shot (0.64). No pair of 8b configs differs (all Holm p = 1.0).
5. **gemma3:4b now says yes to all 30 notes** in both strategies (specificity 0.00). Every 8b
   config beats it (Holm p 0.020–0.024).
6. **False positives still sit in `cues_present`.** These include all 8 of qwen3 few-shot's,
   10 of qwen3 zero-shot's 11, and all of llama3.1's. In `cues_missing` the 8b configs have
   0–1 false positives.
7. **llama3.1's quotes got worse; qwen3's stayed reliable.** Fewer of llama3.1's yes-answer
   quotes appear verbatim in the note (zero-shot 10/15 → 7/12, few-shot 8/10 → 5/7). Under the
   strict rule, zero-shot loses 4 of its 7 true positives (F1 0.67 → 0.38). qwen3's quotes are
   88–90% verified, and the strict rule costs it 1 true positive per strategy. The new rule
   that the quote must be the conversation sentence may be pushing llama3.1 to paraphrase.
8. **The runs were reliable.** All 180 calls succeeded. r0's one gemma3 truncation did not
   recur.

### Takeaways

- **The r1 rules did not reach the main error.** The CMO and planned-meeting rules trimmed a
  couple of llama3.1 false positives but none of qwen3's. Next, triage the r1 false
  positives, starting with qwen3 few-shot, to find which `cues_present` patterns are still
  read as conversations.
- **Watch the recall cost.** llama3.1's precision gains came with an extra miss in each
  strategy. Any new "no" rule should be checked against the 9 gold positives.
- **Revisit the quote rule for llama3.1.** It produces fewer verbatim quotes since r1. Consider
  restating that the quote must be copied exactly from the note.
- **Treat these numbers as directional.** With 9 positives, one note moves recall by about
  0.11, and repeated tuning on the same 30 notes makes later rounds optimistic. Reportable
  results come only from the frozen test sets.
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
| `llama3.1-8b_zero_shot` | 7 / 5 / 2 / 16 | 0.78 (0.45-0.94) | 0.58 (0.32-0.81) | 0.76 (0.55-0.89) | 0.67 | 0 |
| `qwen3-8b_few_shot` | 8 / 8 / 1 / 13 | 0.89 (0.57-0.98) | 0.50 (0.28-0.72) | 0.62 (0.41-0.79) | 0.64 | 0 |
| `llama3.1-8b_few_shot` | 5 / 2 / 4 / 19 | 0.56 (0.27-0.81) | 0.71 (0.36-0.92) | 0.90 (0.71-0.97) | 0.62 | 0 |
| `qwen3-8b_zero_shot` | 9 / 11 / 0 / 10 | 1.00 (0.70-1.00) | 0.45 (0.26-0.66) | 0.48 (0.28-0.68) | 0.62 | 0 |
| `gemma3-4b_few_shot` | 9 / 21 / 0 / 0 | 1.00 (0.70-1.00) | 0.30 (0.17-0.48) | 0.00 (0.00-0.15) | 0.46 | 0 |
| `gemma3-4b_zero_shot` | 9 / 21 / 0 / 0 | 1.00 (0.70-1.00) | 0.30 (0.17-0.48) | 0.00 (0.00-0.15) | 0.46 | 0 |

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 7 / 5 / 1 / 8 | 0.62 (0.36-0.82) | 0 / 0 / 1 / 8 | 1.00 (0.68-1.00) |
| `qwen3-8b_few_shot` | 7 / 8 / 1 / 5 | 0.38 (0.18-0.64) | 1 / 0 / 0 / 8 | 1.00 (0.68-1.00) |
| `llama3.1-8b_few_shot` | 5 / 2 / 3 / 11 | 0.85 (0.58-0.96) | 0 / 0 / 1 / 8 | 1.00 (0.68-1.00) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 1 / 1 / 0 / 7 | 0.88 (0.53-0.98) |
| `gemma3-4b_few_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 1 / 8 / 0 / 0 | 0.00 (0.00-0.32) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 1 / 8 / 0 / 0 | 0.00 (0.00-0.32) |

## Sensitivity analyses

- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens/recall strict | PPV/precision strict | F1 strict |
|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | 0.67 | 0.33 (0.12-0.65) | 0.43 (0.16-0.75) | 0.38 |
| `qwen3-8b_few_shot` | 0.64 | 0.78 (0.45-0.94) | 0.50 (0.27-0.73) | 0.61 |
| `llama3.1-8b_few_shot` | 0.62 | 0.33 (0.12-0.65) | 0.60 (0.23-0.88) | 0.43 |
| `qwen3-8b_zero_shot` | 0.62 | 0.89 (0.57-0.98) | 0.44 (0.25-0.66) | 0.59 |
| `gemma3-4b_few_shot` | 0.46 | 0.56 (0.27-0.81) | 0.50 (0.24-0.76) | 0.53 |
| `gemma3-4b_zero_shot` | 0.46 | 0.67 (0.35-0.88) | 0.25 (0.12-0.45) | 0.36 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `llama3.1-8b_zero_shot` | 7 / 12 | 0 / 0 |
| `qwen3-8b_few_shot` | 14 / 16 | 2 / 2 |
| `llama3.1-8b_few_shot` | 5 / 7 | 0 / 0 |
| `qwen3-8b_zero_shot` | 18 / 20 | 6 / 6 |
| `gemma3-4b_few_shot` | 10 / 30 | 0 / 0 |
| `gemma3-4b_zero_shot` | 24 / 30 | 0 / 0 |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 0 | 0 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 4 | 19 | 0.003 | 0.024 | significant |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 2 | 16 | 0.001 | 0.020 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 1 | 13 | 0.002 | 0.024 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.024 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 4 | 19 | 0.003 | 0.024 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 2 | 16 | 0.001 | 0.020 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 1 | 13 | 0.002 | 0.024 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.024 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 3 | 2 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 6 | 3 | 0.508 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 9 | 4 | 0.267 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 3 | 1 | 0.625 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 6 | 2 | 0.289 | 1.000 | comparable |
| `qwen3-8b_few_shot` | `qwen3-8b_zero_shot` | 3 | 1 | 0.625 | 1.000 | comparable |

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
