# Labeling guide (project members)

You label on **your own computer**, using **your own** MIMIC-III download. You receive only an
ID file, and you send back only a label file. **Never send, paste, screenshot or upload note
text** (email, Slack, Drive, GitHub, ChatGPT...). PhysioNet doesn't allow sharing MIMIC data
within teams, even between credentialed users.

## One-time setup
1. Clone the private repo and install (Python 3.11+):
   `python -m pip install duckdb pandas pyarrow pydantic streamlit`.
2. Download `NOTEEVENTS.csv.gz` from PhysioNet (MIMIC-III v1.4) with your own credentials, and
   put it in `data/raw/noteevents/`.
3. Put the assignment file you were sent (e.g. `dev_B.parquet` or `test_physician.parquet`) in
   `data/assignments/`. It contains IDs only.
4. From the repo root, run `streamlit run src/labeling/app.py`. A browser tab opens on
   `localhost`. The first time, click **Convert NOTEEVENTS** (a few minutes, once).

## Labeling
- Enter your initials in the sidebar and pick your assignment. Notes appear in a fixed random
  order.
- Answer the three tests separately (see the codebook / CLAUDE.md "Operational definition"):
  1. Is an **interaction** with the patient/family/surrogate documented?
  2. Who **participated**?
  3. Were **goals, values, prognosis or future-treatment preferences** in serious illness
     discussed?

  **GOC present** is derived automatically from these three answers.
- If GOC = yes: **paste the exact sentence(s)** from the note as evidence (it's highlighted when
  found) and choose a GOC type.
- If GOC = no: choose a negative reason. Common ones:
  - DNR order with no discussion → `order_only`
  - "palliative consulted" → `consult_only`
  - "will hold a family meeting" → `planned_only`, plus tick *Anticipated*
  - clinicians talking among themselves → `clinician_only`
- Tick *Secondhand* for reported discussions ("per oncologist, goals were discussed"). These
  count as **yes**.
- Set your confidence and click **Save label**. Time spent is recorded automatically. You can go
  back and re-save; the latest save wins.

## Sending labels back
When you're done, share `data/labels/<assignment>_<INITIALS>.jsonl` with the team. It holds
IDs, your choices and evidence *positions* (character offsets), with no note text.
