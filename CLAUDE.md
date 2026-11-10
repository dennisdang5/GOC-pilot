# CLAUDE.md — GOC Detection in MIMIC-III (Pilot)

**What this project is.** We test whether small, locally run open-weight LLMs can tell when a
MIMIC-III clinical note documents a **goals-of-care (GOC) conversation**. MIMIC-III has no GOC
labels, so we build our own: a physician labels a test set and team members label a dev set. We
tune prompts on dev, score the frozen prompts once on test, and then use the best configuration to
"silver-label" the large unlabeled pool (weak supervision).

**Where things stand:** data prep, sampling, labeling, the LLM pipeline and evaluation are all
built. Dev is being tuned in **rounds** (one prompt version each, all kept): see
[`reports/rounds_dev.md`](reports/rounds_dev.md). The next step is the round-1 dev rerun (§5).

---

## 1. ⛔ Data handling rules (read first, no exceptions)

MIMIC-III is governed by the PhysioNet Credentialed Health Data Use Agreement (DUA). The DUA bans
sharing the data with third parties, **including through APIs**. Claude Code is an API.

**Claude must NEVER:**
- `Read`, `cat`, `head`, `tail`, `less`, or otherwise load any file under `data/` into the
  conversation.
- Run a command, or write code, whose terminal output includes note text.
- Put note text into exception messages, logs, or assertion messages. Log `ROW_ID`s instead.
- Print `str(e)` from DuckDB or CSV errors, because they can contain the raw CSV line. Print only
  the exception class name and the table or file involved.
- Echo, quote, or paraphrase note text that appears anywhere.
- Send note text to a hosted model API.
- Build any export that packages note text for sending to someone.

**Working pattern.** Claude writes code → Claude or the user runs it → only **aggregates** come
back into the conversation: counts, rates, precision / recall, confusion matrices, schema errors,
ROW_IDs.

**Debugging against text** uses synthetic notes only:
- `tests/fixtures/synthetic_notes.jsonl`: hand-written fake notes, safe to read (not created
  yet; format in §5).
- Synthetic strings inside tests.
- When a real note fails in an instructive way, the user writes a synthetic note that reproduces
  the pattern.
- If a task seems to need real note text, stop and say so.

**Also enforced:**
- `data/` is gitignored. Notebook outputs are stripped before commit (`nbstripout`).
- Labeling runs locally in the Streamlit app (localhost only, telemetry off). No Google Sheets,
  Airtable, or hosted labeling tools.
- Each labeler uses **their own** PhysioNet download. The PhysioNet FAQ says: "Sharing data within
  teams or classes is not permitted."
  - Only **ID-only** assignment files go out to labelers.
  - Only **text-free** label files come back.
- All LLM inference uses **locally deployed open-weight models** (Ollama, or vLLM via WSL), run on
  the user's own machine or on USC CARC Discovery in the user's owner-only directory
  (`docs/carc.md`). Only the 4 derived parquets the runner needs go to CARC.
- The GitHub repos are **private** and stay private. `reports/` holds exact MIMIC aggregate
  counts, some of them below 10.

---

## 2. Working agreements

- **Every design choice goes to the user first**, with options, trade-offs and a recommendation.
  Code is written only after approval. Purely mechanical defaults may be taken, but say so.
- Concepts before code: explain, confirm, then implement. Small verified steps, not large modules.
- When the data looks wrong, say so rather than coding around it.
- **Ask before committing or pushing.**

---

## 3. Study design

**Goal.** Find out whether local LLMs can identify GOC documentation in MIMIC-III notes,
validated against a small physician-labeled gold standard. Then use the best configuration as a
weak-supervision (silver) labeler for the larger unlabeled pool.

**Scope: Milestone 1 only.** Develop and evaluate an LLM-assisted weak-supervision approach to
identify GOC conversations, using the small human-labeled sets for development and evaluation.
Out of scope this semester (don't build unless asked):
- component-level content / comprehensiveness (former Milestone 2),
- keyword-baseline comparison,
- trade-off analysis.

### 3.1 Note sets

| Set | n | Labeled by | Purpose |
|---|---|---|---|
| **Test** (`test_a`) | 50 | Physician only (single expert) | All reported numbers. Touched **once**. |
| **Test supplement** (`test_b`) | 50 | Physician only | Enriched for positives (added 2026-10-26). Same freeze as test_a. |
| **Dev** | 30 | 5 members × 6 notes, one labeler per note | Prompt tuning and error inspection. |
| **Few-shot examples** | ~6 | Synthetic (hand-written) | In-prompt demonstrations. Can never leak into test. |
| **Unlabeled pool** | everything else (~61.8k) | The best LLM config | Silver labeling (Stage 6). |

Test_a, test_b and dev are disjoint, and no patient appears in more than one of them.
"**Combined**" means test_a + test_b, scored together.

### 3.2 Sampling strata

A **stratum** is the sampling group a note was drawn from. It steers sampling only; **it is not a
label**.

- **cues_present / cues_missing.** One screening phrase list (the **cues**, §4.2) decides this. A
  note that matches any cue is cues_present.
  - Test_a: 35 cues_present + 15 cues_missing. Dev: 21 + 9.
- **strong** (test_b only). The physician labeled only 9/50 test_a notes yes, too few positives to
  estimate sensitivity. test_b adds 50 notes that are:
  - **≥2 cue families** (a cue family is a group of related cues: discussion · transition ·
    surrogate · values), AND
  - charted **≤7 days before** in-hospital death or hospice discharge.
  - Code: `src/sampling/strong.py`.

Sampling rules:
- The design is positive-heavy on purpose. **Never report the raw positive rate as
  representative of MIMIC.**
- The stratum is hidden during labeling. It is kept for analysis, e.g. how much real GOC sits in
  cues_missing.
- **No sampling weights.** All metrics are reported unweighted on the sample, with per-stratum
  breakdowns. Pool-level prevalence comes from the Stage 6 silver labels, not from re-weighting
  test.

### 3.3 Labeling

**Operational definition:**
> A note contains documented GOC communication if it records an **interaction** between clinician(s)
> and the **patient and/or family or surrogate**, in which **goals, values, prognosis, or
> preferences for future treatment in serious illness** were discussed.

"Clinician" includes physicians, nursing, social work, case management and chaplaincy.

Labelers answer **one question per note: GOC present? yes / no / unsure** (`unsure` is stored as
`unclear`). There is no evidence quote, reason or confidence. This form replaced an earlier
"three tests" form with required evidence, to cut labeling effort.

| Case | Label |
|---|---|
| `Code status: DNR` with no documented discussion | no |
| "Palliative care consulted" | no |
| "Will hold family meeting tomorrow" | no |
| Clinicians discussing among themselves | no |
| "Per outpatient oncologist, goals previously discussed" (secondhand) | **yes** |

**Label schema** (`src/labeling/schema.py`). Each save writes one JSON line, and the latest save
per `row_id` wins:
```json
{
  "row_id": 0,
  "assignment": "test_physician | test_physician_b | dev_A .. dev_E",
  "goc_present": "yes | no | unclear",
  "annotator": "initials",
  "labeled_at": "ISO-8601 UTC"
}
```

Labelers work **blind**: no model output, keyword hits or stratum visible, and notes in randomized
order.

### 3.4 Evaluation rules

**Metrics**
- Pilot framing. Report **95% Wilson CIs** on every proportion. (A Wilson interval is a confidence
  interval for a proportion that stays sensible with small counts.)
- **Primary metrics: sensitivity, PPV, F1, specificity.** Never headline accuracy: the sample is
  negative-heavy, so an all-`no` model would score high accuracy with sensitivity 0.
- Report **test_a, test_b and combined** separately, each with per-stratum breakdowns. test_b is
  enriched, so its PPV is not comparable to test_a's.

**Comparing models**
- Don't claim one model beats another unless **McNemar's test** supports it. McNemar compares two
  models on the same notes, using only the notes where exactly one of them is right. Otherwise,
  call the models comparable.

**Scoring variants**
- `unclear` is collapsed to `no` for all metrics. This is the **primary** analysis.
- **exclude_unclear** is a sensitivity analysis that drops notes labeled `unclear`. Models answer
  yes / no only (user decision 2026-10-28), so this removes only notes that humans labeled
  `unclear`.

**Test freeze**
- **The test sets are frozen.** No scoring, error inspection or peeking until prompts are frozen
  on dev.
- Whoever tunes prompts must not open `labels/test_physician_*` in the labeling repo until then.

**Independence and fairness**
- **The screening regex (`src/sampling/`) is a sampling tool, never a method under evaluation.**
  `src/eval/` must not import it (`tests/test_eval_independence.py` enforces this).
- Every LLM evidence span is checked for exact (whitespace-normalized) presence in the source
  note. Report the verification rate per model.
- `[** **]` de-identification placeholders are handled identically for every method.

### 3.5 Limitations to report

- Results describe `'Nursing'`-period admissions only (see the cohort rule, §4.1), not all of
  MIMIC-III.
- Only the 5 kept note types are covered. GOC documented only in nursing or case-management notes
  is out of scope.
- test_b positives are cue-rich by construction. Sensitivity on test_b (and on the combined set)
  is likely optimistic compared with GOC documented in less explicit language.
- The test gold standard is one physician's labels: no human κ, no adjudication, no reliability
  estimate. There are no human evidence spans, so a gold label can only be audited by re-reading
  the note.

### 3.6 Decision log: documented deviations

- **2026-10-26, test_b design.** The `strong` rule was chosen from aggregate yes counts on dev
  **and test_a** labels (`reports/yield_report.json`). This is a user-approved deviation from the
  test freeze, for sampling design only. Only aggregate yes counts by stratum / category / cue were
  inspected: no ROW_IDs, no text, no model output. The regex is not under evaluation. Labeled
  yield of the chosen rule: 8/16.
- **2026-11-06, dev label revisions.** After dev was scored and the model outputs seen, the user
  re-read the 2 dev notes labeled `unclear` and resolved them: ROW_ID 408701 (dev_E) → yes, and
  ROW_ID 654562 (dev_B) → no. The change was appended to the original labelers' files
  (`dev_E_NS.jsonl`, `dev_B_WB.jsonl`) **with the original labelers' initials**, at the user's
  choice, so this entry is the only record that the user made the change. The original `unclear`
  lines remain as history (the latest line wins). Dev only: no test labels were opened. Dev now
  has 9 yes · 21 no · 0 unclear.

---

## 4. Pipeline (ask before changing any decision here)

```
MIMIC CSVs → Parquet → cohort → candidate notes → strata → test/dev samples
           → labeling (local app) → LLM predictions (CARC) → evaluation → silver labels
```
See `ARCHITECTURE.md` for module contracts.

### 4.1 Stage 1 · Data preparation (done)

| Step | File | Output | Result |
|---|---|---|---|
| Scaffold | dirs, `.gitignore`, `pyproject.toml`, nbstripout | — | done |
| CSV → Parquet | `src/ingest/load.py` | `data/parquet/<table>.parquet` | noteevents **2,083,180** ✅ · admissions 58,976 · patients 46,520 · diagnoses_icd 651,047 |
| Profile | `src/ingest/profile.py` | `reports/profile.json` | exact category / discharge-location literals · V667 = 1,020 adm · DEATHTIME = 5,854 · ISERROR = 1 for 886 notes, NULL otherwise (no 0s) |
| Cohort | `src/cohort/build.py` | `data/derived/cohort.parquet` | 14,379 any-reason → **2,609** with a `'Nursing'` note → 2,609 adults · 2,083 patients |
| Candidates | `src/cohort/candidates.py` | `data/derived/candidates.parquet` | 64,809 → −0 empty → −2,968 exact dups → **61,841 notes** · 2,607 adm · 2,081 patients |

**Cohort.** An admission qualifies if it matches ANY of these (OR, not AND):
- `ADMISSIONS.DEATHTIME IS NOT NULL` (898)
- `ADMISSIONS.DISCHARGE_LOCATION ILIKE '%HOSPICE%'` (120)
- `PATIENTS.DOD <= ADMISSIONS.DISCHTIME + INTERVAL 365 DAY` (2,565; 1,550 as the sole reason).
  Uses `PATIENTS.DOD` (hospital + SSN merged).
- `DIAGNOSES_ICD.ICD9_CODE = 'V667'` (196)

Further cohort rules:
- Adults only: `date_sub('year', DOB, ADMITTIME) >= 18`.
- Keep **all** qualifying admissions per patient. Patient overlap is handled at sampling.
- **Restricted to admissions with ≥1 `'Nursing'` note** (`COALESCE(ISERROR, 0) = 0`).
  - This is only a **documentation-period marker**. `'Nursing'` and `'Nursing/other'` almost
    never co-occur (87 of ~43.9k admissions), and Physician / Social Work / General / Consult
    notes exist almost only in `'Nursing'` admissions.
  - Nursing notes themselves are **not** candidates.
- Output columns: `SUBJECT_ID, HADM_ID, ADMITTIME, died_in_hosp, hospice_dc, died_365d, v667`.

**Candidate notes:**
- **Categories kept** (exact literals; trailing spaces matter): `'Physician '`, `'General'`,
  `'Social Work'`, `'Consult'`, `'Discharge summary'`.
- Excluded on purpose: `'Nursing'`, `'Case Management '` (user decision 2026-10-15) and
  `'Nursing/other'`.
- Drop empty notes. Remove **exact** duplicate TEXT within an admission, keeping the lowest
  `ROW_ID`. Near-duplicates are deferred.
- Keep discharge-summary addenda (102), identified by the `DESCRIPTION` column.
- Keep long notes whole, with `n_chars`. Truncation / chunking is decided at the LLM step.
- No chart-time filter. TEXT is stored unmodified.
- Output columns: `ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, DESCRIPTION, CHARTDATE, CHARTTIME,
  n_chars, TEXT`.

Pool shape:
- Physician 54,213 (88%) · General 3,886 · Discharge summary 2,649 · Social Work 1,039 ·
  Consult 54.
- Notes per admission: median 12 (p90 55, max 437).
- 351 patients have ≥2 admissions (max 24).
- Longest note: 53,169 chars (a discharge summary).

### 4.2 Stage 2 · Sampling (done, frozen)

**Cue list** (`src/sampling/cues.py`, 19 cues, case-insensitive, negation ignored), by family:
- **Discussion:** family meeting · goals of care / GOC · discussed code status / DNR / DNI /
  prognosis / goals · end of life · quality of life
- **Transitions:** comfort care / measures / CMO · hospice · palliative · withdraw(al of)
  care / support · redirect(ion of) care
- **Surrogates and documents:**
  - HCP / health care proxy, **only after a talk verb** (spoke with, updated, called...).
    A bare HCP mention mostly just names the proxy.
  - advance directive · MOLST / POLST
- **Values** (direction-neutral language, required): important to him/her/them · matters most ·
  hopes to · wants to be able to · would not want · wishes
- **Not cues** (template headings, measured only): bare `code status` (81% of notes),
  `full code` (56%), `DNR` (22%), `DNI` (14%).
- New phrases are added only with user approval, after measuring them with
  `src/sampling/cue_frequency.py` (→ `reports/cue_frequency.json`).

**Strata** (`src/sampling/strata.py` → `data/derived/strata.parquet`, no text):
- cues_present **15,082 (24.4%)** / cues_missing **46,759**.
- cues_present by category: Physician 12,620 · Discharge summary 1,116 · General 854 ·
  Social Work 486 · Consult 6. That's 1,634 admissions / 1,491 patients.

**Test_a + dev draw** (`src/sampling/draw.py`, seed **20261016**) →
`data/derived/test_sample.parquet` (50) and `dev_sample.parquet` (30):

| | Physician | Discharge summary | General | Social Work | cues_missing (simple random) |
|---|---|---|---|---|---|
| Test cues_present quota | 25 | 4 | 3 | 3 | 15 (drew Phys 12 · Gen 3) |
| Dev cues_present quota | 15 | 2 | 2 | 2 | 9 (drew Phys 9) |

- Consult is skipped (too rare).
- At most **1 note per patient across test + dev**. Test is drawn first, then its patients are
  removed before dev.
- No length filter.
- Columns: `ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, stratum, n_chars, label_order`.
- `draw.py` refuses to overwrite existing samples.

**test_b draw** (`src/sampling/draw_supplement.py`, seed **20261026**) →
`data/derived/test_b_sample.parquet` (50, `stratum = 'strong'`):
- A yield diagnostic came first: `src/sampling/yield_report.py ../GOC-labeler/labels` →
  `reports/yield_report.json` (counts only). On dev + test_a, yes / n was:
  - cues_present 16/56 · cues_missing 1/24
  - Physician + cue 8/40 · non-Physician + cue 8/16
  - ≥2 families 9/19 · ≥3 families 5/5
  - ≤7 d before end event 13/37 (>7 d 1/12)
  - **≥2 families AND ≤7 d: 8/16** (chosen)
- End event = `DEATHTIME`, else `DISCHTIME` if discharged to hospice. Days = CHARTDATE → end date
  (≤7, can be negative).
- Strong pool: 2,594 notes; 2,341 / 630 patients after excluding test + dev patients.
- Quotas: Physician 32 · Discharge summary 6 · General 6 · Social Work 6. 1 note per patient,
  0 patient overlap with test + dev. Refuses to overwrite.

### 4.3 Stage 3 · Labeling (all sets labeled)

**Assignments** (`src/labeling/assign.py` → `data/assignments/`):
- `test_physician` (50: Phys 37 · Gen 6 · DS 4 · SW 3) and `dev_A` … `dev_E` (6 each).
- `test_physician_b` (50: Phys 32 · DS 6 · Gen 6 · SW 6), written when `test_b_sample` exists.
- Existing assignment files are skipped, never overwritten.
- Columns: `ROW_ID, CATEGORY, n_chars, label_order`. Stratum and cues are dropped.

**App** (`src/labeling/app.py`, Streamlit, localhost):
- On first run, converts the labeler's own NOTEEVENTS download.
- Checks that every ROW_ID exists with matching `n_chars`. Mismatches block labeling.
- One yes / no / unsure question per note (no timing).
- Labelers can go back and change answers. The sidebar shows saved answers, and unsaved changes
  are flagged.
- Writes append-only `<assignment>_<INITIALS>.jsonl`.

**Collect** (`src/labeling/collect.py [LABELS_DIR]`): validates returned files and reports
coverage.

**Member guide:** `docs/labeling.md`.

**Labeling repo:** github.com/dennisdang5/GOC-labeler (**private**), cloned at `../GOC-labeler`.
- `python -m src.labeling.export_kit ../GOC-labeler` copies over:
  - the app, the README (from `docs/labeling.md`), `.gitignore` and requirements,
  - ID-only `assignments/*.csv`,
  - a `.labeling-kit` marker. With the marker present, the app uses `assignments/` and
    `labels/` at the repo root.
- **This repo is the source of truth.** Never edit code in the labeling repo; re-export and push
  instead. The export never touches `labels/`.
- Labelers push only their own `labels/<assignment>_<INITIALS>.jsonl`.
- To collect: `git pull` there, then `python -m src.labeling.collect ../GOC-labeler/labels`.

### 4.4 Stage 4 · LLM pipeline (built 2026-10-28; dev run done, prompts not frozen)

A **config** is one model + one prompting strategy, e.g. `qwen3-8b_few_shot`. There are 6.

Decisions (user-approved 2026-10-28):
- **Models** (Ollama 0.40.12, all Q4, 100% GPU): `llama3.1:8b`, `qwen3:8b` (sent
  `think: false`), `gemma3:4b`. The installed `llama3` and `gemma2:2b` are not used.
- **Strategies:** `zero_shot` and `few_shot`.
  - Both share `src/llm/prompts/system.txt` (definition + edge-case table) and `user.txt`.
  - Few-shot adds 4 **synthetic** examples (`src/llm/fewshot.jsonl`: direct yes · secondhand
    yes · hard no (planned meeting) · hard no (CMO status + family update + planned meeting,
    added 2026-11-09)) as prior user / assistant turns.
- **Output** (`src/llm/schema.py`): Ollama structured output (JSON schema), validated with
  pydantic. Fields in order: `evidence_span` (verbatim quote or null) → `goc_present`
  (`yes | no`, no `unclear`).
- **Decoding:** temperature 0, seed 20261028, `num_predict` 400, `num_ctx` **12288** on every
  call.
- **Context:** whole notes, no chunking.
  - Before sending, the prompt length is estimated at 2.5 chars/token. A note that might not fit
    is not sent (error `truncated`).
  - All dev / test_a / test_b notes fit under both strategies. Real prompts are 2–4k tokens.
    With the 2026-11-09 prompts, the largest dev estimate is 5.6k (zero-shot) / 6.9k (few-shot)
    of 12,288, at the conservative 2.5 chars/token.
- **Transport:** `requests` → `localhost:11434/api/chat` (no `ollama` package).
- **Hardware (user decision 2026-10-28):** all runs on **CARC Discovery, `gpu` partition, A100**
  (`slurm/run_llm.sbatch`), using Ollama 0.40.12 with model IDs pinned in `slurm/models.txt`.
  - This followed hard power-offs on the local RTX 3070.
  - Use one GPU type for every set.
  - Partial local dev predictions are not mixed with CARC ones; dev was rerun from scratch there.
- **Test-set guard:** `--set test_a | test_b` is refused unless `src/llm/prompts/FROZEN` exists
  and its prompt hashes match. Create it with `python -m src.llm.run --freeze` only when dev
  tuning is done. "combined" is assembled in eval, not run.

Files:
- `src/llm/run.py --model M --strategy S --set dev [--limit N]` →
  `data/predictions/{model}_{strategy}_{set}.jsonl` (append-only, latest per ROW_ID wins,
  resumable), plus raw replies in `data/predictions/raw/{stem}/{prompt_hash}/`.
  - Resume skips only notes whose latest prediction is error-free **and** has the current prompt
    hash, so a prompt change reruns every note into the same file; older lines stay as history
    (user decision 2026-11-09). Raw replies from the first round sit directly under `{stem}/`.
  - Errors: `parse`, `truncated` (pre-check, or `done_reason = length`).
  - Prints counts, latency, error types and ROW_IDs only.
- `src/llm/validate.py [FILES]`: per-file n, errors, spans and % spans verified
  (whitespace-normalized, case-sensitive exact substring; filled at run time).
- `src/llm/notes.py`: set → ROW_IDs → TEXT, in memory only.
- Speed: ~2–3 s per note once loaded, so a dev run of 6 configs takes ~10 min.

### 4.5 Stage 5 · Evaluation (built 2026-10-29; dev scored)

- `src/eval/metrics.py --set dev | test_a | test_b | combined [--labels DIR] [--pair A B ...]`
  writes, for test sets:
  - `reports/eval_{set}.json` (aggregates),
  - `reports/errors_{set}_{config}.csv` (FP / FN ROW_IDs only; gitignored by `*.csv`).
  - Dev is scored per round instead (see "Prompt-tuning rounds" below).
- `src/eval/report_md.py --set SET [--round rN]` renders that JSON as markdown (no ROW_IDs):
  `reports/results_{set}.md` for test sets, `reports/rounds/dev_rN/results.md` for dev.
  - A hand-written block between `<!-- summary:start -->` and `<!-- summary:end -->` in the
    existing file is kept verbatim under the title on re-render. The script prints a reminder
    when it keeps one.
  - Each dev round's `results.md` uses it for a hand-written Findings + Takeaways summary.
    Update it by hand after scoring a round.
  - For dev, the run line under the title is generated from the round registry: round, run date,
    CARC job, GPU, prompt hashes and what changed. Label revisions and re-scores are not noted
    there; they go in the decision log (§3.6).
  - Table headers read "sensitivity (recall)" and "PPV (precision)" (same metrics, no extra
    columns).

Decisions (user-approved 2026-10-29):
- Gold comes from `../GOC-labeler/labels` via `read_labels`, opening only that set's label files.
  Stratum comes from the sample parquets (`src.llm.notes.SAMPLES`), never `src/sampling/`.
- Scoring variants:
  - **primary**: `unclear` → no.
  - **exclude_unclear**: notes with gold `unclear` dropped.
  - **strict**: a `yes` without a verified span → no.
  - When a set has no gold `unclear` (dev, since 2026-11-06), `report_md.py` omits the unclear
    rule, unclear counts and exclude_unclear columns. They still appear for sets that have any.
- Failed predictions (`parse`, `truncated`) → no, with a failure count per config.
  `num_predict` stays 400.
- Sensitivity, PPV and specificity with Wilson 95% CIs. F1 is a point estimate only (default
  taken). Undefined metrics are `NA`, never 0.
- Per-stratum and (for combined) per-part breakdowns. Strata with <5 gold positives are flagged.
- Spans are reported separately for `yes` and `no` answers (verified / given).
- Exact McNemar on per-note correctness, Holm-adjusted (Holm corrects p-values for testing many
  pairs).
  - Dev: all pairs, exploratory.
  - Test sets: only the pairs named with `--pair`, chosen before the test run.
- Test sets are refused until `FROZEN` exists. A missing gold label or prediction stops the run.
- A config whose latest predictions come from more than one prompt hash (e.g. an unfinished
  rerun) stops the run, listing the hashes and note counts (user decision 2026-11-09).
- Tests: `tests/test_eval_metrics.py` and `tests/test_report_md.py` (synthetic).
- **Prompt-tuning rounds** (user decision 2026-11-09: every dev run is kept and compared).
  - A **round** = one prompt version run on dev. r0 = the 2026-10-29 baseline run.
  - Registry `src/llm/prompt_rounds/rounds.json`: per round, date, prompt hash per strategy, CARC
    job, GPU, what changed. A copy of that round's `system.txt`, `user.txt` and `fewshot.jsonl`
    lives in `src/llm/prompt_rounds/rN/` (synthetic, safe to read).
  - `tests/test_rounds.py` fails if the current prompts don't match the newest round, or if a
    snapshot doesn't reproduce its hashes. So **every prompt edit needs a new round entry**
    (next id, new hashes, one-line "changes", snapshot copy).
  - Predictions for all rounds live in the same append-only files; each line has its
    `prompt_hash`, and eval selects a round by hash (`read_predictions(path, prompt_hash)`).
  - `metrics --set dev [--round rN]` (default: the current prompts' round) →
    `reports/rounds/dev_rN/eval.json` + `errors_{config}.csv`. Refuses to overwrite an existing
    round without `--rescore` (use it only after a label revision, and log that in §3.6).
    eval.json also stores the round, its hashes, the ROW_IDs and a gold fingerprint.
  - `src/eval/compare_rounds.py` → `reports/rounds_dev.md`: rounds table; per config × round
    TP/FP/FN/TN, sensitivity, PPV, specificity (Wilson), F1, strict F1, verified quotes; Δ vs the
    previous round and F1 vs r0; exact McNemar per config for each step, Holm across configs
    within a step ("better" / "worse" only if Holm p < 0.05, else "comparable"). Refuses rounds
    scored on different notes or gold. Reads aggregates only.
  - The triage viewer has a round picker; pattern notes go to
    `data/triage/dev_{round}_patterns.jsonl` (round 0's 15 notes were renamed from
    `dev_patterns.jsonl`).
  - Workflow per round: edit prompts → add round + snapshot → tests → commit / push → CARC
    `git pull` + `sbatch ... dev` → fill `carc_job` → copy predictions back → `metrics --set dev`
    → `report_md --set dev` → hand-written summary → `compare_rounds`.
- **Triage viewer** (`src/eval/triage_app.py`, built 2026-11-09): `streamlit run
  src/eval/triage_app.py`. Localhost, **dev only** (hard-coded), never writes labels.
  - Lists every dev note with ≥1 wrong config (primary rule), most-missed first, with a filter by
    config. Shows the gold label, stratum, each config's answer / outcome / quote, and the note
    with the quotes highlighted.
  - A pattern box appends to `data/triage/dev_{round}_patterns.jsonl` (gitignored). Claude never
    reads it.
  - On dev: 24 error notes (21 gold no, 3 gold yes); 7 are wrong in ≥5 of 6 configs.
  - Tests: `tests/test_triage_app.py` (synthetic).

---

## 5. Status and next steps (2026-11-09)

**Labels (all in):**
- dev 30/30 (5 members; 9 yes, 21 no, 0 unclear after the 2026-11-06 revisions, §3.6).
- test_physician 50/50 (9 yes).
- test_physician_b 50/50, collected 2026-10-28. The yes rate was deliberately not inspected.
- test_a and test_b are frozen.

**CARC Discovery setup (done 2026-10-28):**
- Repo at `~/GOC-pilot` on Discovery (`dennisda`), cloned via a **read-only deploy key**
  (`~/.ssh/id_ed25519_goc`, `Host github.com` entry in `~/.ssh/config`).
  - Code flows PC → GitHub → `git pull` on CARC. Never push from CARC.
- 4 parquets copied (sha256 verified): candidates, dev_sample, test_sample (= test_a),
  test_b_sample. Repo and `data/` are `chmod 700`.
- `carc_setup.sh` done: Python 3.11.9 `.venv`, Ollama 0.40.12 in `~/.local/ollama-0.40.12`,
  models in `/scratch1/dennisda/ollama-models`. All 3 IDs match `slurm/models.txt`.
- Account `xiangren_1987`. The `gpu` partition offers a100, a40, l40s, p100 and v100; we use
  **a100** only.

**Dev run (CARC job 13535035, A100, 2026-10-29):**
- 5 configs ok 30/30. gemma3:4b zero-shot ok 29/30, with 1 `truncated` (ROW_ID 472101: output
  hit `num_predict`, not context).
- Predictions are in `data/predictions/` on the PC (30 lines each).
- Prompt hashes: zero-shot `6a3991073695`, few-shot `c13e3a72a57a`.

**Dev results, round r0 (run 2026-10-29, re-scored 2026-11-06).** Full tables are in
[`reports/rounds/dev_r0/results.md`](reports/rounds/dev_r0/results.md); all rounds side by side in
[`reports/rounds_dev.md`](reports/rounds_dev.md).
- Best by F1: qwen3 few-shot (sens 1.00, PPV 0.53, spec 0.62, F1 0.69) and llama3.1 zero-shot
  (F1 0.67). The 8b configs are statistically indistinguishable (all Holm p = 1.0).
- gemma3:4b says yes to almost everything (spec 0.00–0.05). McNemar puts it below every 8b config
  (Holm p 0.004–0.035).
- The main error is **false positives**, not misses, almost all in `cues_present` notes.
- Dev has only 9 positives, so prompt tuning will be noisy.

**Dev error triage (round 1, done 2026-11-09).**
- Triage viewer: the user found most FPs are notes with a **CMO status / order line** or a
  **planned meeting alongside a family update** (status / logistics, no goals discussed).
- Synthetic notes `syn_001`–`syn_005` in `tests/fixtures/synthetic_notes.jsonl` (drafted by
  Claude from the user's description, checked by the user): CMO status (no) + contrast (yes),
  planned meeting + update (no) + contrast (yes), family update without goals (no). They are
  held-out checks, not few-shot examples.
- Prompt changes (user-approved 2026-11-09):
  - `system.txt`: CMO / comfort orders join the code-status rule. The planned-meeting rule now
    covers "family updated today" and adds that a real conversation plus a planned follow-up is
    still yes. A new test: before yes, find the sentence describing the conversation itself
    (who, and what goals / values / prognosis / preferences). `evidence_span` must be that
    sentence; a status, order, consult, plan or update means null and no.
  - `fewshot.jsonl`: 4th example `syn_d_cmo_update_no` (hard no).
  - New prompt hashes: zero-shot `84e5a005cefb`, few-shot `eea596c7e013`. Registered as round
    **r1** (`src/llm/prompt_rounds/r1/`).
- **gemma3:4b stays** in all runs and results (user decision 2026-11-09).

**▶ Resume here: dev rerun with the round-1 prompts.**
1. On CARC: `git pull`, then rerun all 6 configs on dev (`slurm/run_llm.sbatch`). Resume now
   reruns every note because the hashes changed.
2. Put the job number in `carc_job` for r1 in `src/llm/prompt_rounds/rounds.json`.
3. Copy predictions back, then `python -m src.eval.metrics --set dev` (scores r1),
   `python -m src.eval.report_md --set dev`, write the hand-written summary in
   `reports/rounds/dev_r1/results.md`, and `python -m src.eval.compare_rounds`.
4. Read `reports/rounds_dev.md`. Watch recall: if the best configs lose more than about 1 true
   positive, soften the wording (= round r2). Then decide: another round, or `--freeze`.

**After that:**
1. `--freeze`.
2. A single test run (test_a + test_b).
3. `--set combined` with pre-named `--pair`s.
4. Stage 6, silver labeling: the full pool takes ≈ 2 days per config at ~2.5 s/note, so
   subsample.

**Notes:**
- **Earlier local runs (superseded).** Local dev runs stopped partway when the PC hard-powered-off
  (Kernel-Power 41, no bugcheck; 4 earlier occurrences since June, so likely PSU / stability, not
  the code).
  - Partial local predictions: llama3.1 zero-shot 6/30, few-shot 14/30, others 3-note smoke runs
    only. They are in `data/predictions_local_partial/` and not used in eval.
  - In the smoke runs only 9/15 quotes were verified, and models often gave a quote with `no`.

---

## 6. Reference

### Glossary
- **GOC**: goals of care. See the operational definition in §3.3.
- **Cue / cue family**: a screening phrase / a group of related phrases (§4.2). Used only for
  sampling.
- **Stratum**: the sampling group of a note (cues_present, cues_missing, strong). Not a label.
- **test_a / test_b / combined**: the original test set / the enriched supplement / both
  together.
- **Config**: model + prompting strategy (zero_shot or few_shot).
- **Evidence span**: the verbatim quote a model gives for its answer. It is "verified" if it
  appears exactly in the note.
- **Primary / exclude_unclear / strict**: scoring variants (§4.5).
- **Sensitivity** (= recall): share of true GOC notes the model finds. **PPV**: share of the model's yes
  calls that are right. **Specificity**: share of non-GOC notes the model correctly calls no.
  **F1**: harmonic mean of sensitivity and PPV.
- **Wilson CI**: 95% confidence interval for a proportion, well-behaved at small n.
- **McNemar / Holm**: paired test of two models on the same notes / correction for testing many
  pairs.
- **Silver labels**: LLM-generated labels on the unlabeled pool (weak supervision).

### Repo layout
```
data/                 # GITIGNORED — never read by Claude
  raw/<table>/        # MIMIC CSVs: noteevents, admissions, patients, diagnoses_icd
  parquet/            # one-time Parquet conversion, queried directly by DuckDB
  derived/            # cohort, candidates, strata, test/dev samples
  assignments/        # ID-only labeling assignments
  labels/             # returned label files
  predictions/        # model outputs
src/
  ingest/             # csv → parquet, profile
  cohort/             # cohort + candidate notes
  sampling/           # cues, strata, draw   ← never imported by eval
  labeling/           # Streamlit app, schema, assign, collect, export_kit
  llm/                # schema, prompts/, fewshot.jsonl (synthetic), notes, run, validate
  eval/               # metrics.py (CIs, McNemar, span rates, error ROW_IDs), report_md.py,
                      # triage_app.py (local dev error viewer)
  weak/               # silver labeling of the unlabeled pool (not started)
tests/                # synthetic data only; fixtures/ for synthetic notes
docs/labeling.md      # labeler guide (also the GOC-labeler README)
docs/carc.md          # running the LLM pipeline on USC CARC Discovery
reports/              # aggregate results only
.streamlit/           # local-only app config
```
See `ARCHITECTURE.md` for the pipeline diagram, module contracts and repos.

### Environment
- Python 3.12 in the PyCharm `.venv` (user approved 3.12 over 3.11). `uv` isn't installed;
  install with `.venv/Scripts/python.exe -m pip`.
- Run modules from the repo root as `python -m src.<module>.<file>`. Tests:
  `python -m pytest tests`.
- Installed: `duckdb`, `pandas`, `pyarrow`, `pydantic`, `scikit-learn`, `statsmodels`,
  `streamlit`, `pytest`, `nbstripout`.
- Inference: `ollama` (vLLM needs WSL on Windows).
- Git: github.com/dennisdang5/GOC-pilot is **private** (see §1).

### MIMIC-III gotchas
- Column names are UPPERCASE in the CSVs.
- `NOTEEVENTS.TEXT` contains embedded newlines. Convert with proper CSV quoting, and verify the
  row count is 2,083,180.
- DuckDB queries Parquet files directly (`FROM 'data/parquet/noteevents.parquet'`). There's no
  database server and no `.duckdb` file.
- Category strings vary in case and whitespace. Profile first, then paste exact literals.
- ICD-9 codes have no decimal: V66.7 → `'V667'`.
- Dates are shifted per patient. Intervals are valid; absolute dates are meaningless.
- Filter `COALESCE(ISERROR, 0) = 0`.
- Neonates are included. Age >89 appears as ~300 years; treat >200 as 90+.
