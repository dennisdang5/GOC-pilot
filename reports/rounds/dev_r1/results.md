# Results: dev set, round r1

Round r1: run 2026-11-09, CARC job 13933520 (A100). Prompts: zero-shot `84e5a005cefb`, few-shot `eea596c7e013`. Changes: From dev triage (CMO status lines; planned meeting + family update): CMO / comfort orders join the code-status rule; planned meeting with a family update -> no, real conversation + follow-up -> yes; must find the sentence describing the conversation, and evidence_span must be that sentence; 4th few-shot example (hard no: CMO + update + planned meeting).

<!-- summary:start -->
## Summary

*Hand-written for this round. Re-renders keep this block as-is, so check it against the
tables after a re-score. Numbers use the dev labels as revised on 2026-11-11 (8 yes · 22 no;
CLAUDE.md §3.6).*

### Findings

1. **Round 1 cut false positives without losing recall, but no step is significant.** The
   llama3.1 configs each lost 3 false positives with no new misses (McNemar 0 vs 3 notes,
   p = 0.25, Holm p = 1.0). qwen3 few-shot lost 1 false positive. qwen3 zero-shot gives the same
   answer as r0 on every note. See [`rounds_dev.md`](../../rounds_dev.md).
2. **llama3.1 few-shot now leads on point estimates.** F1 is 0.80 (recall 0.75, PPV 0.86,
   specificity 0.95), up from 0.67 in r0. Next come llama3.1 zero-shot (0.70, up from 0.61),
   qwen3 few-shot (0.67, up from 0.64) and qwen3 zero-shot (0.57, unchanged).
3. **The 8b configs are still statistically tied.** The largest gap, llama3.1 few-shot vs qwen3
   zero-shot (11 vs 2 notes), has p = 0.022 unadjusted but Holm p = 0.16. Every other 8b pair
   has Holm p ≥ 0.42.
4. **gemma3:4b now says yes to all 30 notes** in both strategies (specificity 0.00). Every 8b
   config beats it (Holm p 0.001–0.018).
5. **qwen3 keeps most of its false positives.** It has 8 (few-shot) and 12 (zero-shot), mostly
   in `cues_present`, plus 1–2 in `cues_missing`. llama3.1 has none in `cues_missing`. All 8 gold
   positives sit in `cues_present`, so recall in `cues_missing` cannot be measured on dev.
6. **llama3.1's quotes got worse; qwen3's stayed reliable.** Fewer of llama3.1's yes-answer
   quotes appear verbatim in the note (zero-shot 10/15 → 7/12, few-shot 8/10 → 5/7). Under the
   strict rule, llama3.1 few-shot drops from F1 0.80 to 0.62 and zero-shot from 0.70 to 0.53.
   qwen3's quotes are 88–90% verified, and the strict rule costs it 2 true positives per
   strategy. The new rule that the quote must be the conversation sentence may be pushing
   llama3.1 to paraphrase.
7. **The runs were reliable.** All 180 calls succeeded. r0's one gemma3 truncation did not
   recur.

### Takeaways

- **The r1 rules helped llama3.1 and did little for qwen3.** The next round should target the
  `cues_present` false positives that qwen3 still calls yes.
- **Fix the quotes for llama3.1.** Its yes answers are better, but fewer of its quotes are
  verbatim. Consider restating that the quote must be copied exactly from the note.
- **Watch recall.** Every new "no" rule should be checked against the 8 gold positives.
- **Treat these numbers as directional.** With 8 positives, one note moves recall by about
  0.12. Repeated tuning on the same 30 notes, plus label revisions made after seeing model
  output, make dev optimistic. Reportable results come only from the frozen test sets.
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
| `llama3.1-8b_few_shot` | 6 / 1 / 2 / 21 | 0.75 (0.41-0.93) | 0.86 (0.49-0.97) | 0.95 (0.78-0.99) | 0.80 | 0 |
| `llama3.1-8b_zero_shot` | 7 / 5 / 1 / 17 | 0.88 (0.53-0.98) | 0.58 (0.32-0.81) | 0.77 (0.57-0.90) | 0.70 | 0 |
| `qwen3-8b_few_shot` | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0 |
| `qwen3-8b_zero_shot` | 8 / 12 / 0 / 10 | 1.00 (0.68-1.00) | 0.40 (0.22-0.61) | 0.45 (0.27-0.65) | 0.57 | 0 |
| `gemma3-4b_few_shot` | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0 |
| `gemma3-4b_zero_shot` | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0 |

## By stratum (primary rule)

Shows where the false positives fall. Per-stratum sensitivity and PPV are omitted: `cues_missing` has fewer than 5 gold positives.

| config | `cues_present` TP / FP / FN / TN | `cues_present` specificity | `cues_missing` TP / FP / FN / TN | `cues_missing` specificity |
|---|---|---|---|---|
| `llama3.1-8b_few_shot` | 6 / 1 / 2 / 12 | 0.92 (0.67-0.99) | 0 / 0 / 0 / 9 | 1.00 (0.70-1.00) |
| `llama3.1-8b_zero_shot` | 7 / 5 / 1 / 8 | 0.62 (0.36-0.82) | 0 / 0 / 0 / 9 | 1.00 (0.70-1.00) |
| `qwen3-8b_few_shot` | 8 / 7 / 0 / 6 | 0.46 (0.23-0.71) | 0 / 1 / 0 / 8 | 0.89 (0.57-0.98) |
| `qwen3-8b_zero_shot` | 8 / 10 / 0 / 3 | 0.23 (0.08-0.50) | 0 / 2 / 0 / 7 | 0.78 (0.45-0.94) |
| `gemma3-4b_few_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 0 / 9 / 0 / 0 | 0.00 (0.00-0.30) |
| `gemma3-4b_zero_shot` | 8 / 13 / 0 / 0 | 0.00 (0.00-0.23) | 0 / 9 / 0 / 0 | 0.00 (0.00-0.30) |

## Sensitivity analyses

- **strict**: a model `yes` without a verified evidence span counted as `no`.

| config | F1 primary | sens/recall strict | PPV/precision strict | F1 strict |
|---|---|---|---|---|
| `llama3.1-8b_few_shot` | 0.80 | 0.50 (0.22-0.78) | 0.80 (0.38-0.96) | 0.62 |
| `llama3.1-8b_zero_shot` | 0.70 | 0.50 (0.22-0.78) | 0.57 (0.25-0.84) | 0.53 |
| `qwen3-8b_few_shot` | 0.67 | 0.75 (0.41-0.93) | 0.43 (0.21-0.67) | 0.55 |
| `qwen3-8b_zero_shot` | 0.57 | 0.75 (0.41-0.93) | 0.33 (0.16-0.56) | 0.46 |
| `gemma3-4b_few_shot` | 0.42 | 0.50 (0.22-0.78) | 0.40 (0.17-0.69) | 0.44 |
| `gemma3-4b_zero_shot` | 0.42 | 0.75 (0.41-0.93) | 0.25 (0.12-0.45) | 0.38 |

## Evidence spans

Each quote the model gives is checked for an exact (whitespace-normalized, case-sensitive) match in the note. Shown as verified / given.

| config | on `yes` answers | on `no` answers |
|---|---|---|
| `llama3.1-8b_few_shot` | 5 / 7 | 0 / 0 |
| `llama3.1-8b_zero_shot` | 7 / 12 | 0 / 0 |
| `qwen3-8b_few_shot` | 14 / 16 | 2 / 2 |
| `qwen3-8b_zero_shot` | 18 / 20 | 6 / 6 |
| `gemma3-4b_few_shot` | 10 / 30 | 0 / 0 |
| `gemma3-4b_zero_shot` | 24 / 30 | 0 / 0 |

## Model comparisons (exact McNemar, Holm-adjusted; exploratory, all pairs)

Counts are notes that only A or only B got right. Pairs with Holm p ≥ 0.05 should be called comparable.

| A | B | only A right | only B right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | `gemma3-4b_zero_shot` | 0 | 0 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | `llama3.1-8b_few_shot` | 2 | 21 | <0.001 | <0.001 | significant |
| `gemma3-4b_few_shot` | `llama3.1-8b_zero_shot` | 1 | 17 | <0.001 | 0.002 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_few_shot` | 0 | 14 | <0.001 | 0.002 | significant |
| `gemma3-4b_few_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.018 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_few_shot` | 2 | 21 | <0.001 | <0.001 | significant |
| `gemma3-4b_zero_shot` | `llama3.1-8b_zero_shot` | 1 | 17 | <0.001 | 0.002 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_few_shot` | 0 | 14 | <0.001 | 0.002 | significant |
| `gemma3-4b_zero_shot` | `qwen3-8b_zero_shot` | 0 | 10 | 0.002 | 0.018 | significant |
| `llama3.1-8b_few_shot` | `llama3.1-8b_zero_shot` | 4 | 1 | 0.375 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_few_shot` | 7 | 2 | 0.180 | 0.719 | comparable |
| `llama3.1-8b_few_shot` | `qwen3-8b_zero_shot` | 11 | 2 | 0.022 | 0.157 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_few_shot` | 3 | 1 | 0.625 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | `qwen3-8b_zero_shot` | 7 | 1 | 0.070 | 0.422 | comparable |
| `qwen3-8b_few_shot` | `qwen3-8b_zero_shot` | 4 | 0 | 0.125 | 0.625 | comparable |

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
