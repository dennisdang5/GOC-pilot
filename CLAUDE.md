# CLAUDE.md — GOC Detection in MIMIC-III (Pilot)

## 1. ⛔ Data handling rules (read first, no exceptions)

This repo works with **MIMIC-III**, governed by the PhysioNet Credentialed Health Data Use
Agreement. The DUA prohibits sharing the data with third parties, **including through APIs**.
Claude Code is an API.

**Claude must NEVER:**
- `Read`, `cat`, `head`, `tail`, `less`, or otherwise load any file under `data/` into the conversation
- Run a command or write code whose terminal output includes note text
- Put note text into exception messages, logs, or assertion messages (log `ROW_ID`s instead)
- Print `str(e)` from DuckDB/CSV errors. They can contain the raw CSV line. Print only the
  exception class name and the table/file involved.
- Echo, quote, or paraphrase note text that appears anywhere
- Send note text to a hosted model API
- Build any export that packages note text for sending to someone

**Working pattern:** Claude writes code → Claude or the user runs it → only **aggregates** enter the
conversation (counts, rates, precision/recall, confusion matrices, schema errors, ROW_IDs).

To debug against text, use synthetic notes only: `tests/fixtures/synthetic_notes.jsonl`
(hand-written fake notes, safe to read; not created yet) or synthetic strings inside tests. When a
real note fails in an instructive way, the user writes a synthetic note reproducing the pattern.
If a task seems to require reading real note text, stop and say so.

**Also enforced:**
- `data/` is gitignored. Notebook outputs are stripped before commit (`nbstripout`).
- Labeling happens locally in the Streamlit app (localhost only, telemetry off). No Google Sheets,
  Airtable, or hosted labeling tools.
- Each labeler uses **their own** PhysioNet download. PhysioNet FAQ: "Sharing data within teams or
  classes is not permitted." Only **ID-only** assignment files go out; only **text-free** label
  files come back.
- All LLM inference uses **locally deployed open-weight models** (Ollama, or vLLM via WSL).

---

## 2. How to work with the user

- **Every design choice goes to the user first**: options + trade-offs + a recommendation, approved
  **before** code is written. Purely mechanical defaults may be taken, but say so.
- Concepts before code. Explain, confirm, then implement. Small verified steps, not large modules.
- When the data looks wrong, say so rather than coding around it.
- **Ask before committing or pushing.**

---

## 3. Project

**Goal:** Find out whether local LLMs can identify goals-of-care (GOC) documentation in MIMIC-III
clinical notes, validated against a small physician-labeled gold standard. Then use the best
configuration as a weak-supervision (silver) labeler for the larger unlabeled pool.

MIMIC-III ships raw notes only (`NOTEEVENTS.TEXT`) with no GOC labels. This project creates the
ground truth.

**Scope: Milestone 1 only.** Develop and evaluate an LLM-assisted weak-supervision approach to
identify GOC conversations, using the small human-labeled sets for development and evaluation.
Out of scope this semester (don't build unless asked): component-level content /
comprehensiveness (former M2), keyword-baseline comparison, trade-off analysis.

---

## 4. Study design

### Sets

| Set | n | Labeled by | Purpose |
|---|---|---|---|
| **Test** (test_a) | 50 | Physician only (single expert) | All reported numbers. Touched **once**. |
| **Test supplement** (test_b) | 50 | Physician only | Enriched for positives (added 2026-10-26). Same freeze as test. |
| **Dev** | 30 | 5 members × 6 notes, one labeler per note | Prompt tuning and error inspection |
| **Few-shot examples** | ~6 | Synthetic (hand-written) | In-prompt demonstrations. Can never leak into test. |
| **Unlabeled pool** | everything else (~61.8k) | the best LLM config | Silver labeling (Stage 6) |

Test, test_b and dev are disjoint, and no patient appears in more than one of them.

### Sampling (two strata)
- **Cues present / cues missing**, assigned by one screening phrase list. A note matching any
  phrase is cues-present.
- **Test: 35 cues-present + 15 cues-missing. Dev: 21 + 9.**
- Positive-heavy by design. **Never report the raw positive rate as representative of MIMIC.**
- **The stratum is not a label.** It only steers sampling. It is hidden during labeling and kept
  for analysis (e.g. how much real GOC sits in cues-missing).
- **No sampling weights.** All metrics are reported unweighted on the sample, with per-stratum
  breakdowns. Pool-level prevalence comes from the Stage 6 silver labels, not from re-weighting test.
- **test_b (enriched supplement, 2026-10-26).** The physician labeled only 9/50 test notes yes,
  too few positives to estimate sensitivity. test_b adds 50 notes from a third stratum, `strong`:
  ≥2 cue families AND charted ≤7 days before in-hospital death or hospice discharge
  (`src/sampling/strong.py`). The rule was chosen from aggregate yes counts on dev **and test**
  labels (`reports/yield_report.json`). This is a documented, user-approved deviation from the test
  freeze for sampling design only: no model output was involved and the regex is not under
  evaluation. That labeled yield was 8/16.

### Labeling

**Operational definition:**
> A note contains documented GOC communication if it records an **interaction** between clinician(s)
> and the **patient and/or family or surrogate**, in which **goals, values, prognosis, or
> preferences for future treatment in serious illness** were discussed.

"Clinician" includes physicians, nursing, social work, case management, chaplaincy.

Labelers answer **one question per note: GOC present? yes / no / unsure** (stored as `unclear`).
There is no evidence quote, reason, or confidence. This form replaced an earlier three-tests form
with required evidence, to cut labeling effort.

| Case | Label |
|---|---|
| `Code status: DNR` with no documented discussion | no |
| "Palliative care consulted" | no |
| "Will hold family meeting tomorrow" | no |
| Clinicians discussing among themselves | no |
| "Per outpatient oncologist, goals previously discussed" (secondhand) | **yes** |

**Label schema** (`src/labeling/schema.py`), one JSON line per save, latest save per `row_id` wins:
```json
{
  "row_id": 0,
  "assignment": "test_physician | test_physician_b | dev_A .. dev_E",
  "goc_present": "yes | no | unclear",
  "annotator": "initials",
  "labeled_at": "ISO-8601 UTC"
}
```

### Statistics and evaluation guardrails
- Pilot framing. Report **95% Wilson CIs** on every proportion.
- **Primary metrics: sensitivity, PPV, F1, specificity.** Never use accuracy as a headline: the
  sample is negative-heavy, so an all-`no` model would score high accuracy with sensitivity 0.
- Report **test_a, test_b and combined** separately, each with per-stratum breakdowns. test_b is
  enriched, so its PPV is not comparable to test_a's.
- Don't claim one model beats another unless **McNemar's test** supports it; otherwise call them
  comparable.
- `unclear` is collapsed to `no` for all metrics (primary analysis). Also report a sensitivity
  analysis that excludes `unclear`. Apply the same rule to humans and models.
- **The test set is frozen.** No scoring, error inspection or peeking until prompts are frozen on
  dev. Whoever tunes prompts must not open `labels/test_physician_*` in the labeling repo until
  then. (Exception, 2026-10-26: aggregate yes counts by stratum / category / cue were inspected to
  design test_b. No ROW_IDs, no text, no model output.)
- Labelers work blind (no model output, keyword hits or stratum visible), with notes in randomized
  order.
- **Screening regex (`src/sampling/`) is a sampling tool, never a method under evaluation.**
  `src/eval/` must not import it (`tests/test_eval_independence.py` enforces this).
- Every LLM evidence span is checked for exact (whitespace-normalized) presence in the source note.
  Report the verification rate per model.
- `[** **]` de-identification placeholders are handled identically for every method.

### Limitations to report
- Results describe `'Nursing'`-period admissions only (see cohort rule), not all of MIMIC-III.
- Only the 5 kept note types are covered. GOC documented only in nursing or case-management notes
  is out of scope.
- test_b positives are cue-rich by construction, so sensitivity on test_b (and on the combined
  set) is likely optimistic compared with GOC documented in less explicit language.
- The test gold standard is one physician's labels: no human κ, no adjudication, no reliability
  estimate. There are no human evidence spans, so a gold label can only be audited by re-reading
  the note.

---

## 5. Pipeline: decisions and results (ask before changing any of these)

### Stage 1 · Data preparation — done

| Step | File | Output | Result |
|---|---|---|---|
| Scaffold | dirs, `.gitignore`, `pyproject.toml`, nbstripout | — | done |
| CSV → Parquet | `src/ingest/load.py` | `data/parquet/<table>.parquet` | noteevents **2,083,180** ✅ · admissions 58,976 · patients 46,520 · diagnoses_icd 651,047 |
| Profile | `src/ingest/profile.py` | `reports/profile.json` | exact category / discharge-location literals · V667 = 1,020 adm · DEATHTIME = 5,854 · ISERROR = 1 for 886 notes, NULL otherwise (no 0s) |
| Cohort | `src/cohort/build.py` | `data/derived/cohort.parquet` | 14,379 any-reason → **2,609** with a `'Nursing'` note → 2,609 adults · 2,083 patients |
| Candidates | `src/cohort/candidates.py` | `data/derived/candidates.parquet` | 64,809 → −0 empty → −2,968 exact dups → **61,841 notes** · 2,607 adm · 2,081 patients |

**Cohort** = admissions matching ANY of (OR, not AND):
- `ADMISSIONS.DEATHTIME IS NOT NULL` (898)
- `ADMISSIONS.DISCHARGE_LOCATION ILIKE '%HOSPICE%'` (120)
- `PATIENTS.DOD <= ADMISSIONS.DISCHTIME + INTERVAL 365 DAY` (2,565; 1,550 as sole reason).
  Uses `PATIENTS.DOD` (hospital + SSN merged).
- `DIAGNOSES_ICD.ICD9_CODE = 'V667'` (196)

Further rules:
- Adults only: `date_sub('year', DOB, ADMITTIME) >= 18`.
- Keep **all** qualifying admissions per patient. Patient overlap is handled at sampling.
- **Restricted to admissions with ≥1 `'Nursing'` note** (`COALESCE(ISERROR, 0) = 0`). This is
  only a **documentation-period marker**: `'Nursing'` and `'Nursing/other'` almost never co-occur
  (87 of ~43.9k admissions), and Physician / Social Work / General / Consult notes exist almost
  only in `'Nursing'` admissions. Nursing notes themselves are **not** candidates.
- Output columns: `SUBJECT_ID, HADM_ID, ADMITTIME, died_in_hosp, hospice_dc, died_365d, v667`.

**Candidate notes:**
- **Categories kept** (exact literals; trailing spaces matter): `'Physician '`, `'General'`,
  `'Social Work'`, `'Consult'`, `'Discharge summary'`.
- Excluded on purpose: `'Nursing'`, `'Case Management '` (user decision 2026-10-15) and
  `'Nursing/other'`.
- Drop empty notes. Remove **exact** duplicate TEXT within an admission, keeping the lowest
  `ROW_ID`. Near-duplicates are deferred.
- Keep discharge-summary addenda (102), identified by the `DESCRIPTION` column.
- Keep long notes whole with `n_chars`. Truncation / chunking is decided at the LLM step.
- No chart-time filter. TEXT is stored unmodified.
- Output columns: `ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, DESCRIPTION, CHARTDATE, CHARTTIME,
  n_chars, TEXT`.
- Pool shape:
  - Physician 54,213 (88%) · General 3,886 · Discharge summary 2,649 · Social Work 1,039 ·
    Consult 54.
  - Notes per admission: median 12 (p90 55, max 437).
  - 351 patients have ≥2 admissions (max 24).
  - Longest note 53,169 chars (a discharge summary).

### Stage 2 · Sampling — done (frozen)

**Cue list** (`src/sampling/cues.py`, 19 cues, case-insensitive, negation ignored):
- **Discussion:** family meeting · goals of care / GOC · discussed code status / DNR / DNI /
  prognosis / goals · end of life · quality of life
- **Transitions:** comfort care / measures / CMO · hospice · palliative · withdraw(al of)
  care / support · redirect(ion of) care
- **Surrogates and documents:**
  - HCP / health care proxy, **only after a talk verb** (spoke with, updated, called...).
    Bare HCP mostly just names the proxy.
  - advance directive · MOLST / POLST
- **Direction-neutral value language (required):** important to him/her/them · matters most ·
  hopes to · wants to be able to · would not want · wishes
- **Not cues (template headings, measured only):** bare `code status` (81% of notes), `full code`
  (56%), `DNR` (22%), `DNI` (14%). Add new phrases only with user approval, after measuring them
  with `src/sampling/cue_frequency.py` (→ `reports/cue_frequency.json`).

**Strata** (`src/sampling/strata.py` → `data/derived/strata.parquet`, no text):
- cues_present **15,082 (24.4%)** / cues_missing **46,759**.
- cues_present by category: Physician 12,620 · Discharge summary 1,116 · General 854 ·
  Social Work 486 · Consult 6. That's 1,634 admissions / 1,491 patients.

**Draw** (`src/sampling/draw.py`, seed **20261016**) → `data/derived/test_sample.parquet` (50) and
`dev_sample.parquet` (30):

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

**Supplement test_b** (`src/sampling/draw_supplement.py`, seed **20261026**) →
`data/derived/test_b_sample.parquet` (50, `stratum = 'strong'`):
- Yield diagnostic first: `src/sampling/yield_report.py ../GOC-labeler/labels` →
  `reports/yield_report.json` (counts only). On dev + test, yes/n: cues_present 16/56,
  cues_missing 1/24, Physician + cue 8/40, non-Physician + cue 8/16, ≥2 families 9/19,
  ≥3 families 5/5, ≤7 d before end event 13/37 (>7 d 1/12), **≥2 families AND ≤7 d 8/16**.
- Cue families (`strong.py`): discussion · transition · surrogate · values. End event =
  `DEATHTIME`, else `DISCHTIME` if discharged to hospice; days = CHARTDATE → end date (≤7, can be
  negative).
- Strong pool 2,594 notes; 2,341 / 630 patients after excluding test + dev patients.
- Quotas: Physician 32 · Discharge summary 6 · General 6 · Social Work 6. 1 note per patient,
  0 patient overlap with test + dev. Refuses to overwrite.

### Stage 3 · Labeling — test_a + dev labeled; test_b assigned

- **Assignments** (`src/labeling/assign.py` → `data/assignments/`):
  - `test_physician` (50: Phys 37 · Gen 6 · DS 4 · SW 3) and `dev_A` … `dev_E` (6 each).
  - `test_physician_b` (50: Phys 32 · DS 6 · Gen 6 · SW 6), written when `test_b_sample` exists.
  - Existing assignment files are skipped, never overwritten.
  - Columns `ROW_ID, CATEGORY, n_chars, label_order`. Stratum and cues are dropped.
- **App** (`src/labeling/app.py`, Streamlit, localhost):
  - On first run, converts the labeler's own NOTEEVENTS download.
  - Checks every ROW_ID exists with matching `n_chars`; mismatches block labeling.
  - One yes / no / unsure question per note (no timing).
  - Labelers can go back and change answers: the sidebar shows saved answers, and unsaved
    changes are flagged.
  - Writes append-only `<assignment>_<INITIALS>.jsonl`.
- **Collect** (`src/labeling/collect.py [LABELS_DIR]`): validates returned files and reports
  coverage.
- **Member guide:** `docs/labeling.md`.
- **Labeling repo:** github.com/dennisdang5/GOC-labeler, **private**, cloned at `../GOC-labeler`.
  - `python -m src.labeling.export_kit ../GOC-labeler` copies the app, README (from
    `docs/labeling.md`), `.gitignore`, requirements, ID-only `assignments/*.csv` and a
    `.labeling-kit` marker. With the marker present, the app uses `assignments/` and `labels/`
    at the repo root.
  - **This repo is the source of truth.** Never edit code in the labeling repo; re-export and push
    instead. The export never touches `labels/`.
  - Labelers push only their own `labels/<assignment>_<INITIALS>.jsonl`.
  - To collect: `git pull` there, then `python -m src.labeling.collect ../GOC-labeler/labels`.

---

## 6. Status and next steps (2026-10-26)

**Labels in:** dev 30/30 (5 members) and test_physician 50/50 (9 yes). Because 9 positives is too
few, an enriched 50-note **test_b** was drawn and exported as `assignments/test_physician_b.csv`
for the physician. Collect it when it comes back (`git pull` in `../GOC-labeler`, then `collect`).

**▶ Resume here: LLM step design (`src/llm/`).** Not started: no design choices made, no code
written. Begin by presenting the design choices below (options + trade-offs + recommendation) and
get approval before writing code.

**Open items for the LLM step:**
- Ollama `num_ctx` must be set explicitly (otherwise silent truncation). Decide long-note handling.
- Hardware: RTX 3070, 8 GB VRAM, so models ≤ ~8B at Q4. Ollama 0.35.1 installed (has `gemma2:2b`,
  `llama3`). vLLM would need WSL.
- Models: 3–4 local open-weight models across families/sizes. Strategies: zero-shot and few-shot.
  Structured JSON output validated with pydantic.
- Full-pool silver labeling ≈ days per config; consider subsampling.

**Git:** github.com/dennisdang5/GOC-pilot is **private**. Keep it private: `reports/` holds exact
MIMIC aggregate counts, some < 10.

---

## 7. Reference

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
  llm/                # prompts, runners, output validation (not started)
  eval/               # metrics, CIs, McNemar, error analysis (not started)
  weak/               # silver labeling of the unlabeled pool (not started)
tests/                # synthetic data only; fixtures/ for synthetic notes
docs/labeling.md      # labeler guide (also the GOC-labeler README)
reports/              # aggregate results only
.streamlit/           # local-only app config
```
See `ARCHITECTURE.md` for the pipeline diagram, module contracts and repos.

### Environment
- Python 3.12 in the PyCharm `.venv` (user approved 3.12 over 3.11). `uv` isn't installed;
  install with `.venv/Scripts/python.exe -m pip`.
- Run modules from the repo root as `python -m src.<module>.<file>`. Tests: `python -m pytest tests`.
- Installed: `duckdb`, `pandas`, `pyarrow`, `pydantic`, `scikit-learn`, `statsmodels`,
  `streamlit`, `pytest`, `nbstripout`.
- Inference: `ollama` (vLLM needs WSL on Windows).

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
