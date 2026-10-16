# CLAUDE.md — GOC Detection in MIMIC-III (Pilot)

## ⛔ Data handling rules (read first, no exceptions)

This repo works with **MIMIC-III**, governed by the PhysioNet Credentialed Health Data Use
Agreement. The DUA prohibits sharing the data with third parties, **including through APIs**.
Claude Code is an API.

**Claude must NEVER:**

- `Read`, `cat`, `head`, `tail`, `less`, or otherwise load any file under `data/` into the conversation
- Run a command or write code whose terminal output includes note text
- Put note text into exception messages, logs, or assertion messages (log `ROW_ID`s instead)
- Print `str(e)` from DuckDB/CSV errors — they can contain the raw CSV line. Print only the
  exception class name and the table/file involved.
- Echo, quote, or paraphrase note text that appears anywhere
- Send note text to a hosted model API

**Working pattern:** Claude writes code → Claude or the user runs it → only **aggregates** enter the
conversation (counts, rates, κ, precision/recall, confusion matrices, schema errors, ROW_IDs).

To debug against text, use `tests/fixtures/synthetic_notes.jsonl` (hand-written fake notes, safe to
read). When a real note fails in an instructive way, the user writes a synthetic note reproducing the
pattern and adds it to the fixtures.

If a task seems to require reading real note text, stop and say so.

**Also enforced:**
- `data/` is gitignored. Notebook outputs stripped before commit (`nbstripout`).
- Labeling happens locally. No Google Sheets, Airtable, or hosted labeling tools.
- All LLM inference uses **locally deployed open-weight models** (vLLM or Ollama).

---

## Project

**Goal:** Determine whether local LLMs can identify goals-of-care (GOC) documentation in MIMIC-III
clinical notes, validated against a small physician-reviewed gold standard, and use the best
configuration as a weak-supervision labeler for the larger unlabeled corpus.

MIMIC-III ships raw notes only (`NOTEEVENTS.TEXT`) with no GOC labels. Ground truth is created by
this project.

### Scope: Milestone 1 only

**M1.** Develop and evaluate an LLM-assisted weak-supervision approach to identify GOC conversations,
using a small human-reviewed gold standard for model development and evaluation.

Out of scope this semester (future work): component-level content/comprehensiveness (former M2),
keyword-baseline comparison, trade-off analysis. Do not build these unless asked.

---

## Pilot design

| Set | n | Labeled by | Purpose |
|---|---|---|---|
| **Test** | 50 | Annotator + physician, independently, then adjudicated | All reported numbers. Touched **once**. |
| **Dev** | ~30 | Single annotator | Prompt tuning and error inspection |
| **Few-shot examples** | ~6 | Synthetic (hand-written) | In-prompt demonstrations |
| **Unlabeled pool** | rest of candidates | — | Weak-supervision (silver) labeling |

Test and dev are disjoint samples. Few-shot examples are synthetic, so they can never leak into test.

**Test sampling:** 25 strong-cue / 15 weak-cue / 10 background. Positive-heavy by design; never
report the raw positive rate as representative of MIMIC.

**Statistical framing:** pilot. Report 95% Wilson CIs on every proportion. Do not claim one model
beats another unless McNemar's test supports it; otherwise describe them as comparable.

---

## Labeling

### Operational definition

> A note contains documented GOC communication if it records an **interaction** between clinician(s)
> and the **patient and/or family or surrogate**, in which **goals, values, prognosis, or
> preferences for future treatment in serious illness** were discussed.

Three tests, judged separately; `goc_present` is derived. "Clinician" includes physicians, nursing,
social work, case management, chaplaincy.

### Explicit negatives

| Case | Label |
|---|---|
| `Code status: DNR` with no documented discussion | no — `order_only` |
| "Palliative care consulted" | no — `consult_only` |
| "Will hold family meeting tomorrow" | no — `planned_only`, `anticipated: true` |
| Clinicians discussing among themselves | no — `clinician_only` |
| "Per outpatient oncologist, goals previously discussed" | **yes**, `secondhand: true` |

### Label schema — every labeled note

```json
{
  "row_id": 0,
  "interaction_documented": "yes|no|unclear",
  "participants": ["patient|family|surrogate|clinician_only|unclear"],
  "content_relevant": "yes|no|unclear",
  "goc_present": "yes|no|unclear",
  "evidence_span": "verbatim, required if goc_present=yes",
  "negative_reason": "order_only|consult_only|planned_only|clinician_only|no_serious_illness_context|no_goc_content|null",
  "goc_type": "family_meeting|code_status|prognosis_disclosure|hospice_transition|acp_general|other|null",
  "secondhand": false,
  "anticipated": false,
  "annotator": "initials",
  "confidence": 1,
  "minutes_spent": 0
}
```

---

## Decisions already made (ask before changing)

**Cohort** — admissions matching ANY (OR, not AND):
- `ADMISSIONS.DEATHTIME IS NOT NULL`
- `ADMISSIONS.DISCHARGE_LOCATION ILIKE '%HOSPICE%'`
- `PATIENTS.DOD <= ADMISSIONS.DISCHTIME + INTERVAL 365 DAY`
- `DIAGNOSES_ICD.ICD9_CODE = 'V667'`

Adults only.

AND restricted to admissions with ≥1 `'Nursing'` note where `COALESCE(ISERROR, 0) = 0`
(decided 2026-10-06). `'Nursing'` and `'Nursing/other'` almost never co-occur in an admission
(87 of ~43.9k), and Physician / Social Work / Case Management / General / Consult notes exist
almost only in `'Nursing'` admissions. The restriction keeps one documentation period with the
full note mix. Provisional size: 2,609 admissions, 148,438 candidate notes.

**Note categories kept** (exact literals from `reports/profile.json`; trailing spaces matter):
`'Physician '`, `'General'`, `'Social Work'`, `'Consult'`, `'Discharge summary'`.
`'Nursing/other'` is excluded on purpose (see above). `'Nursing'` and `'Case Management '` were
dropped from the candidate pool on 2026-10-15 (user decision). The cohort rule requiring ≥1
`'Nursing'` note **stays**: it only marks the documentation period, and nursing notes are never
candidates.

**Limitations to report:** silver-label prevalence estimates (Stage 6) describe `'Nursing'`-period
admissions only, not all of MIMIC-III. Gold and silver results cover the 5 kept note types only.
GOC documented only in nursing or case-management notes counts as out of scope.

**Strata:** strong-cue / weak-cue / background via screening regex. The weak-cue regex must include
direction-neutral value language (`important to (him|her)`, `matters most`, `hopes to`,
`wants to be able to`).

**Models:** 3–4 local open-weight models across families/sizes that fit available GPU.
Strategies: zero-shot and few-shot. Structured JSON output validated with pydantic.

---

## Guardrails

- **Screening regex (`src/sampling/`) is a sampling tool, never a method under evaluation.**
  `src/eval/` must not import it. A test enforces this.
- **Test set is frozen.** No scoring, no error inspection, no peeking until prompts are frozen on dev.
- Annotators label blind (no model or keyword output visible), notes in randomized order.
- Report Cohen's κ **before** adjudication; keep both raw and adjudicated labels.
- `unclear` labels are collapsed to `no` for κ and all metrics (primary analysis). Report a
  sensitivity analysis excluding `unclear`. Apply the same rule to humans and models.
- Every LLM `evidence_span` is checked for exact (whitespace-normalized) presence in the source note.
  Report the verification rate per model.
- `[** **]` de-identification placeholders: handled identically for every method.

---

## Current status — WHERE WE LEFT OFF (2026-10-06)

**Process rule from the user:** every design choice is brought to the user with options +
trade-offs + a recommendation, and approved **before** code is written. Defaults that are purely
mechanical may be taken, but say so.

### Done (Stage 1 · data preparation) — all run, verified, committed

| Step | File | Output | Result |
|---|---|---|---|
| 1. Scaffold | dirs, `.gitignore`, `pyproject.toml`, nbstripout filter | — | committed + pushed (private repo) |
| 2. CSV → Parquet | `src/ingest/load.py` | `data/parquet/<table>.parquet` | noteevents **2,083,180** ✅; admissions 58,976; patients 46,520; diagnoses_icd 651,047 |
| 3. Profile | `src/ingest/profile.py` | `reports/profile.json` | exact category / discharge-location literals; V667 = 1,020 adm; DEATHTIME = 5,854; ISERROR = 1 for 886 notes, NULL otherwise (no 0s) |
| 4. Cohort | `src/cohort/build.py` | `data/derived/cohort.parquet` | 14,379 any-reason → **2,609** with `'Nursing'` note → 2,609 adult; 2,083 patients |
| 5. Candidates | `src/cohort/candidates.py` | `data/derived/candidates.parquet` | (re-run 2026-10-15, 5 categories) 64,809 → −0 empty → −2,968 exact dups → **61,841 notes**, 2,607 adm (2 cohort adm have no candidates), 2,081 patients |

Approved choices (beyond "Decisions already made"):
- **Cohort:** 365-day rule uses `PATIENTS.DOD` (hosp + SSN merged); keep **all** qualifying
  admissions per patient (patient overlap handled at sampling); adult = `date_sub('year', DOB,
  ADMITTIME) >= 18`. Output columns: `SUBJECT_ID, HADM_ID, ADMITTIME, died_in_hosp, hospice_dc,
  died_365d, v667`. Reason counts: died_365d 2,565 (1,550 sole reason), died_in_hosp 898,
  v667 196, hospice_dc 120.
- **Candidates:** remove **exact** duplicate TEXT within an admission (keep lowest `ROW_ID`;
  near-dups deferred); keep discharge-summary addenda (102) with `DESCRIPTION` column; drop
  empty notes, keep long notes whole with `n_chars` (truncation/chunking decided at LLM step);
  no chart-time filter; TEXT stored unmodified (`[** **]` handled later, identically for all
  methods). Output columns: `ROW_ID, SUBJECT_ID, HADM_ID, CATEGORY, DESCRIPTION, CHARTDATE,
  CHARTTIME, n_chars, TEXT`.

Candidate pool shape (for sampling design): Physician 54,213 · General 3,886 ·
Discharge summary 2,649 · Social Work 1,039 · Consult 54. Physician = 88%.
Notes/admission median 12 (p90 55, max 437). 351 patients have ≥2 admissions (max 24).
Longest note 53,169 chars (discharge summary).

### NEXT — `src/sampling/strata.py` (not started; present design choices first)

Choices to bring to the user:
- Strong-cue vs weak-cue phrase lists (weak-cue must include direction-neutral value language —
  see "Strata" above); case-insensitivity; handling negation ("no family meeting").
- Stratum precedence when a note matches both (strong wins?).
- Then `sampling/draw.py`: category balance (Social Work etc. are rare), cap notes per admission,
  keep each patient in only one of test/dev, fixed seed.
- Also pending: write the test that `src/eval/` never imports `src/sampling/`.

### Open items to raise later
- LLM step: Ollama `num_ctx` must be set explicitly (silent truncation); long-note handling.
- Hardware: RTX 3070, 8 GB VRAM → models ≤ ~8B at Q4. Ollama 0.35.1 installed (has `gemma2:2b`,
  `llama3`). vLLM would need WSL. Full-pool silver labeling ≈ days per config; consider subsampling.
- Git: Stage 1 committed and pushed to `origin/main` (github.com/dennisdang5/GOC-pilot, **private**
  — keep it private; `reports/` holds exact MIMIC aggregate counts, some < 10). Ask before committing.

---

## Repo layout

See `ARCHITECTURE.md` for the pipeline and data contracts.

```
data/                 # GITIGNORED — never read by Claude
  raw/
    noteevents/       # ← NOTEEVENTS csv here
    admissions/       # ← ADMISSIONS csv here
    patients/         # ← PATIENTS csv here
    diagnoses_icd/    # ← DIAGNOSES_ICD csv here
  parquet/            # one-time Parquet conversion, queried directly by DuckDB
  derived/            # cohort, candidates, strata, samples
  labels/             # gold + dev labels
  predictions/        # model outputs
src/
  ingest/             # csv → parquet
  cohort/             # cohort + candidate notes
  sampling/           # strata + samplers   ← never imported by eval
  labeling/           # local CLI labeling tool, schemas
  llm/                # prompts, runners, output validation
  eval/               # metrics, κ, CIs, McNemar, error analysis
  weak/               # silver labeling of unlabeled pool
tests/fixtures/       # synthetic notes — safe to read
docs/codebook.md
reports/              # aggregate results only
```

---

## Environment

Python 3.12 in the PyCharm `.venv` (user approved 3.12 over 3.11; `uv` not installed — packages
installed with `.venv/Scripts/python.exe -m pip`). Run modules from the repo root as
`python -m src.<module>.<file>`. `duckdb`, `pandas`, `pyarrow`, `pydantic`, `scikit-learn`,
`statsmodels`, `pytest`, `nbstripout` installed. Inference: `ollama` (vLLM needs WSL on Windows).

---

## MIMIC-III gotchas

- MIMIC-III column names are UPPERCASE in the CSVs.
- `NOTEEVENTS.TEXT` contains embedded newlines. Convert with proper CSV quoting; verify row count = 2,083,180.
- DuckDB queries Parquet files directly (`FROM 'data/parquet/noteevents.parquet'`). No database server or `.duckdb` file.
- Category strings vary in case/whitespace. Profile first, paste exact literals.
- ICD-9 codes have no decimal: V66.7 → `'V667'`.
- Dates are shifted per patient. Intervals valid, absolute dates meaningless.
- Filter `COALESCE(ISERROR, 0) = 0`.
- Neonates included. Age >89 appears as ~300 years; treat >200 as 90+.

---

## Working style

Concepts before code. Explain, confirm, then implement. Small verified steps, not large modules.
When the data looks wrong, say so rather than coding around it.
