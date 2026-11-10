# Prompt-tuning rounds: dev

Each round is one version of the prompts run on the 30 dev notes. All rounds are scored against the same gold labels. Dev is for tuning: none of these numbers are reportable.

## Rounds

| round | date | CARC job (GPU) | zero-shot prompt | few-shot prompt | what changed |
|---|---|---|---|---|---|
| **r0** | 2026-10-29 | 13535035 (A100) | `6a3991073695` | `c13e3a72a57a` | Baseline: GOC definition + edge-case rules; few-shot adds 3 synthetic examples (direct yes, secondhand yes, hard no: planned meeting). |
| **r1** (not scored yet) | 2026-11-09 | — (A100) | `84e5a005cefb` | `eea596c7e013` | From dev triage (CMO status lines; planned meeting + family update): CMO / comfort orders join the code-status rule; planned meeting with a family update -> no, real conversation + follow-up -> yes; must find the sentence describing the conversation, and evidence_span must be that sentence; 4th few-shot example (hard no: CMO + update + planned meeting). |

## Results by round (primary rule)

Proportions show the estimate and its 95% Wilson CI. Configs are sorted by F1 in the newest round (r0).

| config | round | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | F1 strict | quotes verified (yes) |
|---|---|---|---|---|---|---|---|---|
| `qwen3-8b_few_shot` | r0 | 9 / 8 / 0 / 13 | 1.00 (0.70-1.00) | 0.53 (0.31-0.74) | 0.62 (0.41-0.79) | 0.69 | 0.67 | 15 / 17 |
| `llama3.1-8b_zero_shot` | r0 | 8 / 7 / 1 / 14 | 0.89 (0.57-0.98) | 0.53 (0.30-0.75) | 0.67 (0.45-0.83) | 0.67 | 0.53 | 10 / 15 |
| `llama3.1-8b_few_shot` | r0 | 6 / 4 / 3 / 17 | 0.67 (0.35-0.88) | 0.60 (0.31-0.83) | 0.81 (0.60-0.92) | 0.63 | 0.47 | 8 / 10 |
| `qwen3-8b_zero_shot` | r0 | 9 / 11 / 0 / 10 | 1.00 (0.70-1.00) | 0.45 (0.26-0.66) | 0.48 (0.28-0.68) | 0.62 | 0.54 | 17 / 20 |
| `gemma3-4b_zero_shot` | r0 | 9 / 20 / 0 / 1 | 1.00 (0.70-1.00) | 0.31 (0.17-0.49) | 0.05 (0.01-0.23) | 0.47 | 0.29 | 19 / 29 |
| `gemma3-4b_few_shot` | r0 | 9 / 21 / 0 / 0 | 1.00 (0.70-1.00) | 0.30 (0.17-0.48) | 0.00 (0.00-0.15) | 0.46 | 0.53 | 10 / 30 |

Only one round has been scored, so there is nothing to compare yet.

## How to read this

- Same 30 dev notes and the same gold labels for every round (current labels, including the 2026-11-06 revisions).
- Dev has 9 gold positives: one note moves sensitivity by about 0.11, so most round-to-round changes are within noise. Rely on the McNemar column, not the deltas.
- Prompts were tuned on these same notes, so later rounds are optimistic on dev. Only the frozen test sets give reportable numbers.
- Per-round details: `reports/rounds/dev_{round}/results.md`. Prompt files of each round: `src/llm/prompt_rounds/{round}/`.
