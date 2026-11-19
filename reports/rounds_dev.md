# Prompt-tuning rounds: dev

Each round is one version of the prompts run on the 30 dev notes. All rounds are scored against the same gold labels. Dev is for tuning: none of these numbers are reportable.

## Rounds

| round | date | CARC job (GPU) | zero-shot prompt | few-shot prompt | what changed |
|---|---|---|---|---|---|
| **r0** | 2026-10-29 | 13535035 (A100) | `6a3991073695` | `c13e3a72a57a` | Baseline: GOC definition + edge-case rules; few-shot adds 3 synthetic examples (direct yes, secondhand yes, hard no: planned meeting). |
| **r1** | 2026-11-09 | 13933520 (A100) | `84e5a005cefb` | `eea596c7e013` | From dev triage (CMO status lines; planned meeting + family update): CMO / comfort orders join the code-status rule; planned meeting with a family update -> no, real conversation + follow-up -> yes; must find the sentence describing the conversation, and evidence_span must be that sentence; 4th few-shot example (hard no: CMO + update + planned meeting). |
| **r2** | 2026-11-11 | 14030227 (A100) | `98dca2eeac05` | `70187780106a` | User-written system prompt: two tests, (A) a conversation with the patient/family/HCP already happened, or they made an overall-direction decision (CMO, withdrawal, hospice, stop chemo), and (B) it has content (goals, values, prognosis shared, or a treatment preference/decision); 9 always-no patterns (code status, empty templates, planned talks, updates, team plans/consults, content-free meetings, medical management, comfort orders, stated preferences + referral), 3 yes patterns, a 4-step procedure; evidence_span must pass A and B. Few-shot: 16 synthetic examples (6 yes, 10 no), replacing the 4. num_ctx 12288 -> 16384 from r2 on, so every test note fits under few-shot. |
| **r3** | 2026-11-19 | 14366175 (A100) | `98dca2eeac05` | `152a46a1e633` | r2 system/user prompt unchanged, with the 4 r1 few-shot examples instead of the 16 r2 examples (tests whether the 16 examples hurt few-shot). Zero-shot prompt is identical to r2 (same hash), so r2's zero-shot predictions are reused, not rerun. |

## Results by round (primary rule)

Proportions show the estimate and its 95% Wilson CI. Configs are sorted by F1 in the newest round (r3).

- **quotes verified (yes)**: each `yes` answer comes with a quote from the note as evidence. This counts how many of those quotes were found in the note word for word (verified / given). It covers all `yes` answers, right or wrong.
- **grounded recall**: of the gold-`yes` notes, the share the model called `yes` with a verified quote. A bad quote can only lower it.

| config | round | TP / FP / FN / TN | sensitivity (recall) | PPV (precision) | specificity | F1 | grounded recall | quotes verified (yes) |
|---|---|---|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | r0 | 7 / 8 / 1 / 14 | 0.88 (0.53-0.98) | 0.47 (0.25-0.70) | 0.64 (0.43-0.80) | 0.61 | 0.62 (0.31-0.86) | 10 / 15 |
| `llama3.1-8b_zero_shot` | r1 | 7 / 5 / 1 / 17 | 0.88 (0.53-0.98) | 0.58 (0.32-0.81) | 0.77 (0.57-0.90) | 0.70 | 0.50 (0.22-0.78) | 7 / 12 |
| `llama3.1-8b_zero_shot` | r2 | 8 / 3 / 0 / 19 | 1.00 (0.68-1.00) | 0.73 (0.43-0.90) | 0.86 (0.67-0.95) | 0.84 | 0.75 (0.41-0.93) | 8 / 11 |
| `llama3.1-8b_zero_shot` | r3 | 8 / 3 / 0 / 19 | 1.00 (0.68-1.00) | 0.73 (0.43-0.90) | 0.86 (0.67-0.95) | 0.84 | 0.75 (0.41-0.93) | 8 / 11 |
| `llama3.1-8b_few_shot` | r0 | 6 / 4 / 2 / 18 | 0.75 (0.41-0.93) | 0.60 (0.31-0.83) | 0.82 (0.61-0.93) | 0.67 | 0.50 (0.22-0.78) | 8 / 10 |
| `llama3.1-8b_few_shot` | r1 | 6 / 1 / 2 / 21 | 0.75 (0.41-0.93) | 0.86 (0.49-0.97) | 0.95 (0.78-0.99) | 0.80 | 0.50 (0.22-0.78) | 5 / 7 |
| `llama3.1-8b_few_shot` | r2 | 6 / 4 / 2 / 18 | 0.75 (0.41-0.93) | 0.60 (0.31-0.83) | 0.82 (0.61-0.93) | 0.67 | 0.50 (0.22-0.78) | 7 / 10 |
| `llama3.1-8b_few_shot` | r3 | 6 / 2 / 2 / 20 | 0.75 (0.41-0.93) | 0.75 (0.41-0.93) | 0.91 (0.72-0.97) | 0.75 | 0.62 (0.31-0.86) | 6 / 8 |
| `qwen3-8b_few_shot` | r0 | 8 / 9 / 0 / 13 | 1.00 (0.68-1.00) | 0.47 (0.26-0.69) | 0.59 (0.39-0.77) | 0.64 | 0.75 (0.41-0.93) | 15 / 17 |
| `qwen3-8b_few_shot` | r1 | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0.75 (0.41-0.93) | 14 / 16 |
| `qwen3-8b_few_shot` | r2 | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0.75 (0.41-0.93) | 13 / 16 |
| `qwen3-8b_few_shot` | r3 | 8 / 8 / 0 / 14 | 1.00 (0.68-1.00) | 0.50 (0.28-0.72) | 0.64 (0.43-0.80) | 0.67 | 0.50 (0.22-0.78) | 12 / 16 |
| `qwen3-8b_zero_shot` | r0 | 8 / 12 / 0 / 10 | 1.00 (0.68-1.00) | 0.40 (0.22-0.61) | 0.45 (0.27-0.65) | 0.57 | 0.75 (0.41-0.93) | 17 / 20 |
| `qwen3-8b_zero_shot` | r1 | 8 / 12 / 0 / 10 | 1.00 (0.68-1.00) | 0.40 (0.22-0.61) | 0.45 (0.27-0.65) | 0.57 | 0.75 (0.41-0.93) | 18 / 20 |
| `qwen3-8b_zero_shot` | r2 | 8 / 11 / 0 / 11 | 1.00 (0.68-1.00) | 0.42 (0.23-0.64) | 0.50 (0.31-0.69) | 0.59 | 0.62 (0.31-0.86) | 14 / 19 |
| `qwen3-8b_zero_shot` | r3 | 8 / 11 / 0 / 11 | 1.00 (0.68-1.00) | 0.42 (0.23-0.64) | 0.50 (0.31-0.69) | 0.59 | 0.62 (0.31-0.86) | 14 / 19 |
| `gemma3-4b_few_shot` | r0 | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0.62 (0.31-0.86) | 10 / 30 |
| `gemma3-4b_few_shot` | r1 | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0.50 (0.22-0.78) | 10 / 30 |
| `gemma3-4b_few_shot` | r2 | 7 / 10 / 1 / 12 | 0.88 (0.53-0.98) | 0.41 (0.22-0.64) | 0.55 (0.35-0.73) | 0.56 | 0.75 (0.41-0.93) | 12 / 15 |
| `gemma3-4b_few_shot` | r3 | 8 / 20 / 0 / 2 | 1.00 (0.68-1.00) | 0.29 (0.15-0.47) | 0.09 (0.03-0.28) | 0.44 | 0.62 (0.31-0.86) | 7 / 28 |
| `gemma3-4b_zero_shot` | r0 | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0.50 (0.22-0.78) | 19 / 29 |
| `gemma3-4b_zero_shot` | r1 | 8 / 22 / 0 / 0 | 1.00 (0.68-1.00) | 0.27 (0.14-0.44) | 0.00 (0.00-0.15) | 0.42 | 0.75 (0.41-0.93) | 24 / 30 |
| `gemma3-4b_zero_shot` | r2 | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0.62 (0.31-0.86) | 15 / 29 |
| `gemma3-4b_zero_shot` | r3 | 8 / 21 / 0 / 1 | 1.00 (0.68-1.00) | 0.28 (0.15-0.46) | 0.05 (0.01-0.22) | 0.43 | 0.62 (0.31-0.86) | 15 / 29 |

## Change from the previous round

Point-estimate differences (new minus previous); `F1 vs r0` compares with the first round. One dev note moves sensitivity by about 0.12.

| config | step | Δ FP | Δ FN | Δ sensitivity | Δ PPV | Δ specificity | Δ F1 | F1 vs r0 |
|---|---|---|---|---|---|---|---|---|
| `llama3.1-8b_zero_shot` | r0 → r1 | -3 | +0 | 0.00 | +0.12 | +0.14 | +0.09 | +0.09 |
| `llama3.1-8b_zero_shot` | r1 → r2 | -2 | -1 | +0.12 | +0.14 | +0.09 | +0.14 | +0.23 |
| `llama3.1-8b_zero_shot` | r2 → r3 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | +0.23 |
| `llama3.1-8b_few_shot` | r0 → r1 | -3 | +0 | 0.00 | +0.26 | +0.14 | +0.13 | +0.13 |
| `llama3.1-8b_few_shot` | r1 → r2 | +3 | +0 | 0.00 | -0.26 | -0.14 | -0.13 | 0.00 |
| `llama3.1-8b_few_shot` | r2 → r3 | -2 | +0 | 0.00 | +0.15 | +0.09 | +0.08 | +0.08 |
| `qwen3-8b_few_shot` | r0 → r1 | -1 | +0 | 0.00 | +0.03 | +0.05 | +0.03 | +0.03 |
| `qwen3-8b_few_shot` | r1 → r2 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | +0.03 |
| `qwen3-8b_few_shot` | r2 → r3 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | +0.03 |
| `qwen3-8b_zero_shot` | r0 → r1 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `qwen3-8b_zero_shot` | r1 → r2 | -1 | +0 | 0.00 | +0.02 | +0.05 | +0.02 | +0.02 |
| `qwen3-8b_zero_shot` | r2 → r3 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | +0.02 |
| `gemma3-4b_few_shot` | r0 → r1 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| `gemma3-4b_few_shot` | r1 → r2 | -12 | +1 | -0.12 | +0.15 | +0.55 | +0.14 | +0.14 |
| `gemma3-4b_few_shot` | r2 → r3 | +10 | -1 | +0.12 | -0.13 | -0.45 | -0.12 | +0.02 |
| `gemma3-4b_zero_shot` | r0 → r1 | +1 | +0 | 0.00 | -0.01 | -0.05 | -0.01 | -0.01 |
| `gemma3-4b_zero_shot` | r1 → r2 | -1 | +0 | 0.00 | +0.01 | +0.05 | +0.01 | 0.00 |
| `gemma3-4b_zero_shot` | r2 → r3 | +0 | +0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

## Did each step help? (exact McNemar, Holm across configs within each step)

Counts are notes only the previous round or only the new round got right. "better" / "worse" need Holm p < 0.05; otherwise the rounds are comparable.

How the test works, in plain terms:

- It ignores notes that both rounds got right or both got wrong, and looks only at the notes where they disagree.
- If the new round wins most of those notes, the change is probably real. If the split is close to even, it could just be luck.
- **p** is the chance of a split at least this lopsided if the change made no real difference. Below 0.05 counts as a real change.
- **Holm p** raises the bar, because we run one test per config at every step. The more tests you run, the more likely one passes by luck.

| config | step | only previous right | only new right | p | Holm p |  |
|---|---|---|---|---|---|---|
| `gemma3-4b_few_shot` | r0 → r1 | 0 | 0 | 1.000 | 1.000 | comparable |
| `gemma3-4b_zero_shot` | r0 → r1 | 1 | 0 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | r0 → r1 | 0 | 3 | 0.250 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | r0 → r1 | 0 | 3 | 0.250 | 1.000 | comparable |
| `qwen3-8b_few_shot` | r0 → r1 | 0 | 1 | 1.000 | 1.000 | comparable |
| `qwen3-8b_zero_shot` | r0 → r1 | 0 | 0 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | r1 → r2 | 1 | 12 | 0.003 | 0.021 | better |
| `gemma3-4b_zero_shot` | r1 → r2 | 0 | 1 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | r1 → r2 | 5 | 2 | 0.453 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | r1 → r2 | 1 | 4 | 0.375 | 1.000 | comparable |
| `qwen3-8b_few_shot` | r1 → r2 | 0 | 0 | 1.000 | 1.000 | comparable |
| `qwen3-8b_zero_shot` | r1 → r2 | 1 | 2 | 1.000 | 1.000 | comparable |
| `gemma3-4b_few_shot` | r2 → r3 | 10 | 1 | 0.012 | 0.070 | comparable |
| `gemma3-4b_zero_shot` | r2 → r3 | 0 | 0 | 1.000 | 1.000 | comparable |
| `llama3.1-8b_few_shot` | r2 → r3 | 1 | 3 | 0.625 | 1.000 | comparable |
| `llama3.1-8b_zero_shot` | r2 → r3 | 0 | 0 | 1.000 | 1.000 | comparable |
| `qwen3-8b_few_shot` | r2 → r3 | 0 | 0 | 1.000 | 1.000 | comparable |
| `qwen3-8b_zero_shot` | r2 → r3 | 0 | 0 | 1.000 | 1.000 | comparable |

## How to read this

- Same 30 dev notes and the same gold labels for every round (current labels, including all revisions logged in CLAUDE.md §3.6).
- Dev has 8 gold positives: one note moves sensitivity by about 0.12, so most round-to-round changes are within noise. Rely on the McNemar column, not the deltas.
- Prompts were tuned on these same notes, so later rounds are optimistic on dev. Only the frozen test sets give reportable numbers.
- Per-round details: `reports/rounds/dev_{round}/results.md`. Prompt files of each round: `src/llm/prompt_rounds/{round}/`.
