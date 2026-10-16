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
- Answer **GOC present? yes / no / unclear**. **Yes** means the note records an
  **interaction** between clinician(s) and the **patient and/or family or surrogate**, in which
  **goals, values, prognosis, or preferences for future treatment in serious illness** were
  discussed. "Clinician" includes nursing, social work, case management and chaplaincy.
- If **yes**: **paste the exact sentence(s)** from the note as evidence (required; it's
  highlighted when found). Tick *Secondhand* for reported discussions ("per oncologist, goals were
  discussed"). These still count as **yes**.
- If **no**: optionally pick a reason. These cases are all **no**:
  - DNR / code status order with no discussion documented → *Order only*
  - "Palliative care consulted" → *Consult only*
  - "Will hold family meeting tomorrow" → *Planned only*
  - Clinicians discussing among themselves → *Clinicians discussing among themselves*
- Use **unclear** only when you genuinely can't decide.
- Click **Save label**. Time spent is recorded automatically. You can go back and re-save; the
  latest save wins.

## Sending labels back
When you're done, share `data/labels/<assignment>_<INITIALS>.jsonl` with the team. It holds
IDs, your choices and evidence *positions* (character offsets), with no note text.
