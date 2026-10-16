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
- Answer **GOC present? yes / no / unsure**, then click **Save label**. That's all.
- **Yes** means the note records an **interaction** between clinician(s) and the **patient and/or
  family or surrogate**, in which **goals, values, prognosis, or preferences for future treatment
  in serious illness** were discussed. "Clinician" includes nursing, social work, case management
  and chaplaincy. A reported discussion counts as **yes** ("per oncologist, goals were
  discussed").
- These are all **no**:
  - DNR / code status order with no discussion documented
  - "Palliative care consulted"
  - "Will hold family meeting tomorrow" (planned, not yet happened)
  - Clinicians discussing among themselves
- Use **unsure** only when you genuinely can't decide.
- Time spent is recorded automatically. You can go back and re-save; the latest save wins.

## Sending labels back
When you're done, share `data/labels/<assignment>_<INITIALS>.jsonl` with the team. It holds
IDs and your yes/no/unsure answers, with no note text.
