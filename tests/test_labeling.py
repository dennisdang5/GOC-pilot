"""Labeling helpers, schema rules and assignment split (synthetic data only)."""

import pandas as pd
import pytest
from pydantic import ValidationError

from src.labeling.assign import split_dev
from src.labeling.derive import find_evidence
from src.labeling.schema import GOCLabel


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
    rec = dict(row_id=1, assignment="dev_A", goc_present="yes", evidence_start=0,
               evidence_end=10, annotator="TT", minutes_spent=2.5,
               labeled_at="2026-10-16T00:00:00+00:00")
    rec.update(kw)
    return rec


NO = dict(goc_present="no", evidence_start=None, evidence_end=None)


@pytest.mark.parametrize("changes", [
    {},
    dict(secondhand=True),
    NO,
    dict(NO, negative_reason="order_only"),
    dict(goc_present="unclear", evidence_start=None, evidence_end=None),
])
def test_valid_labels(changes):
    GOCLabel.model_validate(base(**changes))


@pytest.mark.parametrize("changes", [
    dict(evidence_start=None, evidence_end=None),              # yes needs evidence
    dict(evidence_end=None),                                   # positions set together
    dict(evidence_start=10, evidence_end=5),
    dict(negative_reason="consult_only"),                      # reason only for no
    dict(goc_present="no"),                                    # no can't carry evidence
    dict(NO, secondhand=True),                                 # secondhand only for yes
    dict(goc_present="maybe"),
    dict(annotator="T1"),
])
def test_invalid_labels(changes):
    with pytest.raises(ValidationError):
        GOCLabel.model_validate(base(**changes))


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
