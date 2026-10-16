"""Local GOC labeling app (Streamlit). Runs on this computer only; never upload note text.

Run from the repo root:  streamlit run src/labeling/app.py

Reads an ID-only assignment file from data/assignments/, pulls the note text from YOUR OWN
local MIMIC-III copy (data/parquet/noteevents.parquet, built from data/raw/noteevents/ on first
run), and appends labels to data/labels/<assignment>_<initials>.jsonl. Label files hold IDs,
choices and evidence character positions only -- no note text -- so they can be sent back.

Set GOC_DATA_DIR to point at a different data folder (used by the tests with synthetic notes).
"""

import html
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # `streamlit run` doesn't put the repo root on the path
    sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from src.ingest.load import EXPECTED_ROWS, convert  # noqa: E402
from src.labeling.derive import derive_goc, find_evidence  # noqa: E402
from src.labeling.schema import GOCLabel  # noqa: E402

DATA = Path(os.environ.get("GOC_DATA_DIR", ROOT / "data"))
NOTES = DATA / "parquet" / "noteevents.parquet"
ASSIGN_DIR = DATA / "assignments"
LABEL_DIR = DATA / "labels"

YNU = ["yes", "no", "unclear"]
PARTICIPANTS = ["patient", "family", "surrogate", "clinician_only", "unclear"]
NEG_REASONS = [None, "order_only", "consult_only", "planned_only", "clinician_only",
               "no_serious_illness_context", "no_goc_content"]
GOC_TYPES = [None, "family_meeting", "code_status", "prognosis_disclosure",
             "hospice_transition", "acp_general", "other"]

st.set_page_config(page_title="GOC labeling", layout="wide")


# ---------- data ----------

def setup_notes() -> None:
    """One-time NOTEEVENTS csv -> parquet conversion, from the labeler's own download."""
    st.title("GOC labeling — one-time setup")
    st.write("Put your own PhysioNet download of `NOTEEVENTS.csv.gz` (or `.csv`) in "
             f"`{(DATA / 'raw' / 'noteevents').as_posix()}/`, then convert it once.")
    if st.button("Convert NOTEEVENTS (takes a few minutes)"):
        NOTES.parent.mkdir(parents=True, exist_ok=True)
        try:
            with st.spinner("Converting..."):
                n = convert(duckdb.connect(), "noteevents", DATA / "raw", DATA / "parquet")
        except Exception as e:
            st.error(f"Conversion failed ({type(e).__name__}). Check the file location.")
            return
        if n != EXPECTED_ROWS["noteevents"]:
            NOTES.unlink(missing_ok=True)
            st.error(f"Row count {n:,} != expected {EXPECTED_ROWS['noteevents']:,}. "
                     "Re-download NOTEEVENTS from PhysioNet.")
            return
        st.success(f"Done: {n:,} notes.")
        st.rerun()


@st.cache_data(show_spinner="Loading your assigned notes...")
def load_notes(assignment_path: str) -> pd.DataFrame:
    a = pd.read_parquet(assignment_path).sort_values("label_order", ignore_index=True)
    con = duckdb.connect()
    con.register("a", a)
    notes = con.execute(f"""
        SELECT a.ROW_ID, a.CATEGORY, a.n_chars, a.label_order, n.TEXT
        FROM a LEFT JOIN '{NOTES.as_posix()}' n USING (ROW_ID)
        ORDER BY a.label_order
    """).df()
    return notes


def labels_path(assignment: str, annotator: str) -> Path:
    return LABEL_DIR / f"{assignment}_{annotator}.jsonl"


def read_own_labels(path: Path) -> dict[int, dict]:
    """Latest record per ROW_ID from this annotator's own file only (blind to others)."""
    latest = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                latest[rec["row_id"]] = rec
    return latest


# ---------- UI ----------

def pick(options: list, value) -> int | None:
    """Radio index for a saved value; None (nothing selected) for a new note."""
    return options.index(value) if value in options else None


def note_html(text: str, span: tuple[int, int] | None) -> str:
    if span:
        s, e = span
        body = (html.escape(text[:s]) + "<mark>" + html.escape(text[s:e]) + "</mark>"
                + html.escape(text[e:]))
    else:
        body = html.escape(text)
    return ("<div style='height:70vh;overflow-y:auto;white-space:pre-wrap;font-family:monospace;"
            f"font-size:0.85rem;border:1px solid #8884;padding:0.75rem'>{body}</div>")


def main() -> None:
    if not NOTES.exists():
        setup_notes()
        return

    files = sorted(p.stem for p in ASSIGN_DIR.glob("*.parquet"))
    with st.sidebar:
        st.header("GOC labeling")
        annotator = st.text_input("Your initials", key="annotator").strip().upper()
        if not files:
            st.warning(f"Put your assignment file in `{ASSIGN_DIR.as_posix()}/`.")
            return
        assignment = st.selectbox("Assignment", files, key="assignment")
    if not annotator.isalpha() or len(annotator) > 5:
        st.info("Enter your initials (letters only) in the sidebar to start.")
        return

    notes = load_notes((ASSIGN_DIR / f"{assignment}.parquet").as_posix())
    missing = notes["TEXT"].isna()
    wrong_len = ~missing & (notes["TEXT"].str.len() != notes["n_chars"])
    if missing.any() or wrong_len.any():
        st.error(f"Your local NOTEEVENTS doesn't match the assignment: {int(missing.sum())} notes "
                 f"missing, {int(wrong_len.sum())} with a different length. Tell the coordinator; "
                 "don't label.")
        return

    out = labels_path(assignment, annotator)
    done = read_own_labels(out)
    n = len(notes)
    if "idx" not in st.session_state or st.session_state.get("idx_for") != (assignment, annotator):
        unlabeled = [i for i, r in enumerate(notes["ROW_ID"]) if r not in done]
        st.session_state.idx = unlabeled[0] if unlabeled else 0
        st.session_state.idx_for = (assignment, annotator)

    with st.sidebar:
        st.progress(len(done) / n, text=f"{len(done)} of {n} labeled")
        options = list(range(n))
        st.session_state.idx = st.selectbox(
            "Go to note", options, index=st.session_state.idx,
            format_func=lambda i: f"{i + 1}. {'✓' if notes.at[i, 'ROW_ID'] in done else '·'}")
        c1, c2 = st.columns(2)
        if c1.button("◀ Prev", disabled=st.session_state.idx == 0):
            st.session_state.idx -= 1
            st.rerun()
        if c2.button("Next ▶", disabled=st.session_state.idx == n - 1):
            st.session_state.idx += 1
            st.rerun()

    i = st.session_state.idx
    row = notes.iloc[i]
    row_id, text = int(row["ROW_ID"]), row["TEXT"]
    prev = done.get(row_id, {})
    timer_key = f"opened_{row_id}"
    st.session_state.setdefault(timer_key, time.time())

    def k(name: str) -> str:  # widget keys are per note so answers don't leak between notes
        return f"{name}_{row_id}"

    left, right = st.columns([3, 2])
    with right:
        st.subheader(f"Note {i + 1} of {n}")
        st.caption(f"ROW_ID {row_id} · {row['CATEGORY'].strip()} · {len(text):,} chars"
                   + (" · already labeled (saving replaces it)" if prev else ""))
        interaction = st.radio("1. Interaction with patient/family/surrogate documented?", YNU,
                               index=pick(YNU, prev.get("interaction_documented")),
                               horizontal=True, key=k("interaction"))
        participants = st.multiselect("2. Participants", PARTICIPANTS,
                                      default=prev.get("participants", []), key=k("participants"))
        content = st.radio("3. Goals / values / prognosis / future-treatment preferences discussed?",
                           YNU, index=pick(YNU, prev.get("content_relevant")),
                           horizontal=True, key=k("content"))
        answered = interaction and participants and content
        goc = derive_goc(interaction, participants, content) if answered else None
        st.markdown(f"**GOC present (derived): `{goc or 'answer 1-3'}`**")

        prev_span = (prev["evidence_start"], prev["evidence_end"]) \
            if prev.get("evidence_start") is not None else None
        pasted = st.text_area("Evidence — paste the exact sentence(s) from the note "
                              "(required if GOC = yes)",
                              value=text[prev_span[0]:prev_span[1]] if prev_span else "",
                              key=k("evidence"), height=100)
        span = find_evidence(text, pasted) if pasted.strip() else None
        if pasted.strip():
            if span:
                st.success("Evidence found in the note (highlighted).")
            else:
                st.error("Not found in the note — paste it exactly as written.")

        neg = st.selectbox("Negative reason (if GOC = no)", NEG_REASONS,
                           index=NEG_REASONS.index(prev.get("negative_reason")),
                           format_func=lambda x: "—" if x is None else x, key=k("neg"))
        gtype = st.selectbox("GOC type (if GOC = yes)", GOC_TYPES,
                             index=GOC_TYPES.index(prev.get("goc_type")),
                             format_func=lambda x: "—" if x is None else x, key=k("gtype"))
        c1, c2 = st.columns(2)
        secondhand = c1.checkbox("Secondhand", value=prev.get("secondhand", False),
                                 key=k("secondhand"))
        anticipated = c2.checkbox("Anticipated / planned", value=prev.get("anticipated", False),
                                  key=k("anticipated"))
        confidence = st.slider("Confidence (1 = guess, 5 = certain)", 1, 5,
                               value=prev.get("confidence", 3), key=k("confidence"))

        if st.button("Save label", type="primary", key=k("save")):
            elapsed = (time.time() - st.session_state[timer_key]) / 60
            record = {
                "row_id": row_id, "assignment": assignment,
                "interaction_documented": interaction, "participants": participants,
                "content_relevant": content, "goc_present": goc,
                "evidence_start": span[0] if span else None,
                "evidence_end": span[1] if span else None,
                "negative_reason": neg, "goc_type": gtype,
                "secondhand": secondhand, "anticipated": anticipated,
                "annotator": annotator, "confidence": confidence,
                "minutes_spent": round(prev.get("minutes_spent", 0) + elapsed, 1),
                "labeled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if not answered:
                st.error("Answer questions 1–3 first.")
            elif pasted.strip() and not span:
                st.error("Fix the evidence first: it isn't in the note.")
            else:
                try:
                    label = GOCLabel.model_validate(record)
                except ValidationError as e:
                    for err in e.errors():
                        st.error(err["msg"].removeprefix("Value error, "))
                else:
                    LABEL_DIR.mkdir(parents=True, exist_ok=True)
                    with out.open("a", encoding="utf-8") as f:
                        f.write(label.model_dump_json() + "\n")
                    st.session_state.pop(timer_key, None)
                    if i < n - 1:
                        st.session_state.idx = i + 1
                    st.rerun()

    with left:
        st.markdown(note_html(text, span), unsafe_allow_html=True)


main()
