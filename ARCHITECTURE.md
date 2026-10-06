# Architecture — GOC Detection in MIMIC-III (Pilot, Milestone 1)

## Pipeline overview

```mermaid
flowchart TD
    subgraph DATA["Stage 1 · Data preparation"]
        RAW[MIMIC-III CSVs<br/>NOTEEVENTS · ADMISSIONS<br/>PATIENTS · DIAGNOSES_ICD] --> ING[ingest<br/>csv → Parquet]
        ING --> PROF[profile<br/>counts only]
        ING --> COH[cohort<br/>died · hospice · died ≤1yr · V667]
        COH --> CAND[candidate notes<br/>adults · kept categories · ISERROR=0]
        CAND --> STRAT[strata<br/>strong · weak · background]
    end

    subgraph SAMPLE["Stage 2 · Sampling"]
        STRAT --> TEST[Test sample<br/>50 notes<br/>25 / 15 / 10]
        STRAT --> DEV[Dev sample<br/>~30 notes]
        STRAT --> POOL[Unlabeled pool<br/>everything else]
    end

    subgraph GOLD["Stage 3 · Human labeling (local CLI)"]
        TEST --> LA[Annotator]
        TEST --> LB[Annotator B · Physician]
        LA --> KAPPA[κ before adjudication]
        LB --> KAPPA
        KAPPA --> ADJ[Adjudication]
        ADJ --> GT[(gold_test)]
        DEV --> LD[Single annotator] --> GD[(gold_dev)]
    end

    subgraph LLM["Stage 4 · LLM pipeline"]
        SYN[Synthetic few-shot<br/>~6 notes] --> PROMPT[Prompt templates<br/>zero-shot · few-shot]
        PROMPT --> RUN[Local runner<br/>vLLM / Ollama<br/>models × strategies]
        RUN --> VAL[Validator<br/>JSON schema · span check]
        VAL --> PRED[(predictions)]
    end

    subgraph EVAL["Stage 5 · Evaluation"]
        GD --> TUNE[Dev loop<br/>error triage by category]
        PRED --> TUNE
        TUNE -->|revise| PROMPT
        TUNE -->|freeze| FROZEN[Frozen prompts]
        FROZEN --> ONCE[Single test run]
        GT --> METRICS[Metrics<br/>P · R · F1 · κ · 95% CI · McNemar]
        ONCE --> METRICS
    end

    subgraph WEAK["Stage 6 · Weak supervision"]
        METRICS --> BEST[Best config]
        BEST --> SILVER[Silver labels on pool]
        POOL --> SILVER
        SILVER --> EST[Error-corrected prevalence]
        SILVER -.stretch.-> BERT[BERT student]
        BERT -.-> METRICS
    end

```

---

## Modules and data contracts

Every stage reads from and writes to `data/`. No stage prints note text.

| Module | Input | Output | Prints |
|---|---|---|---|
| `ingest/load.py` | `data/raw/<table>/*.csv*` | `data/parquet/<table>.parquet` | row counts per table |
| `ingest/profile.py` | parquet | `reports/profile.json` | category counts, discharge locations, V667 count |
| `cohort/build.py` | parquet | `derived/cohort.parquet` (SUBJECT_ID, HADM_ID, reason flags) | count per inclusion reason |
| `cohort/candidates.py` | cohort + NOTEEVENTS | `derived/candidates.parquet` (ROW_ID, HADM_ID, CATEGORY, TEXT) | count per category |
| `sampling/strata.py` | candidates | `derived/strata.parquet` (ROW_ID, stratum) | stratum × category table |
| `sampling/draw.py` | strata, seed | `derived/{test,dev,pool}_ids.parquet` | sizes; asserts disjoint |
| `labeling/cli.py` | sample ids + parquet | `labels/{annotator}_{set}.jsonl` | progress only |
| `labeling/adjudicate.py` | two annotator files | `labels/gold_test.jsonl`, `reports/agreement.json` | κ per field |
| `llm/run.py` | ids, model, strategy | `predictions/{model}_{strategy}_{set}.jsonl` | throughput, parse failures |
| `llm/validate.py` | predictions + notes | adds `span_verified` | % valid JSON, % spans verified |
| `eval/metrics.py` | gold + predictions | `reports/{set}_metrics.json` | metrics table |
| `eval/triage.py` | dev gold + predictions | `reports/dev_errors.json` | errors by `negative_reason`, `goc_type`, stratum |
| `weak/silver.py` | pool ids, frozen config | `predictions/silver_pool.jsonl` | label distribution |

### Prediction record (shared by every method)

```json
{
  "row_id": 0,
  "method": "qwen-14b",
  "strategy": "few_shot",
  "goc_present": "yes",
  "evidence_span": "...",
  "span_verified": true,
  "negative_reason": null,
  "goc_type": "family_meeting",
  "raw_output_path": "predictions/raw/....txt",
  "latency_s": 4.2
}
```

Every model × strategy writes this same shape, so `eval/` treats them identically.

---

## Isolation boundaries

```
src/sampling/  ──X──>  src/eval/        (import forbidden; enforced by test)
gold_test      ──X──>  dev loop         (test never read before prompts are frozen)
synthetic      ──────>  prompts          (only source of few-shot examples)
```

---

## Milestone 1 → stages

| Stage | Delivers |
|---|---|
| 1–2 Data prep + sampling | Candidate pool, 50 test / ~30 dev samples |
| 3 Human labeling | Gold standard + inter-annotator κ |
| 4–5 LLM pipeline + evaluation | Model × strategy metrics with 95% CIs |
| 6 Weak supervision | Silver labels on the pool, error-corrected prevalence |

Future work (not built): component-level content analysis, keyword-baseline comparison.
