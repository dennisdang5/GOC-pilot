"""Labeling helpers, schema rules and assignment split (synthetic data only)."""

import pandas as pd
import pytest
from pydantic import ValidationError

from src.labeling.assign import split_dev
from src.labeling.derive import derive_goc, find_evidence
from src.labeling.schema import GOCLabel


@pytest.mark.parametrize("interaction, participants, content, expected", [
    ("yes", ["family"], "yes", "yes"),
    ("yes", ["patient", "surrogate"], "yes", "yes"),
    ("yes", ["clinician_only"], "yes", "no"),
    ("no", ["family"], "yes", "no"),
    ("yes", ["family"], "no", "no"),
    ("unclear", ["family"], "yes", "unclear"),
    ("yes", ["unclear"], "yes", "unclear"),
    ("unclear", ["unclear"], "no", "no"),
])
def test_derive_goc(interaction, participants, content, expected):
    assert derive_goc(interaction, participants, content) == expected


NOTE = "Pt intubated.\n\nMet with  wife\nand daughter;\tthey wish to\nfocus on comfort."


@pytest.mark.parametrize("pasted", [
    "Met with wife and daughter; they wish to focus on comfort.",
    "  Met with  wife\nand daughter;\tthey wish to\nfocus on comfort.  ",
])
def test_find_evidence_whitespace_normalized(pasted):
    start, end = find_evidence(NOTE, pasted)
    assert NOTE[start:end].startswith("Met with")
    assert NOTE[start:end].endswith("comfort.")


@pytest.mark.parametrize("pasted", ["met with wife", "focus on hospice", "", "   "])
def test_find_evidence_not_found(pasted):
    assert find_evidence(NOTE, pasted) is None


def base(**kw):
    rec = dict(row_id=1, assignment="dev_A", interaction_documented="yes",
               participants=["family"], content_relevant="yes", goc_present="yes",
               evidence_start=0, evidence_end=10, goc_type="family_meeting",
               annotator="TT", confidence=4, minutes_spent=2.5,
               labeled_at="2026-10-16T00:00:00+00:00")
    rec.update(kw)
    return rec


def test_valid_yes_label():
    GOCLabel.model_validate(base())


@pytest.mark.parametrize("changes", [
    dict(goc_present="no"),                                    # doesn't match the three tests
    dict(evidence_start=None, evidence_end=None),              # yes needs evidence
    dict(goc_type=None),                                       # yes needs goc_type
    dict(negative_reason="consult_only"),                      # yes can't have a negative reason
    dict(participants=["family", "clinician_only"]),           # clinician_only is exclusive
    dict(evidence_end=None),                                   # positions set together
    dict(confidence=6),
    dict(annotator="T1"),
    dict(interaction_documented="no", goc_present="no", goc_type=None),  # no needs a reason
])
def test_invalid_labels(changes):
    with pytest.raises(ValidationError):
        GOCLabel.model_validate(base(**changes))


def test_valid_no_label():
    GOCLabel.model_validate(base(interaction_documented="no", goc_present="no", goc_type=None,
                                 evidence_start=None, evidence_end=None,
                                 negative_reason="order_only"))


def test_split_dev_chunks():
    dev = pd.DataFrame({"ROW_ID": range(100, 130), "CATEGORY": "General",
                        "n_chars": 10, "label_order": list(range(30, 0, -1))})
    parts = split_dev(dev, ["A", "B", "C", "D", "E"])
    assert list(parts) == ["dev_A", "dev_B", "dev_C", "dev_D", "dev_E"]
    assert all(len(df) == 6 for df in parts.values())
    assert all(list(df["label_order"]) == [1, 2, 3, 4, 5, 6] for df in parts.values())
    ids = pd.concat([df["ROW_ID"] for df in parts.values()])
    assert ids.is_unique and len(ids) == 30
    assert "stratum" not in parts["dev_A"].columns
