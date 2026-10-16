"""Label schema and assignment split (synthetic data only)."""

import pandas as pd
import pytest
from pydantic import ValidationError

from src.labeling.assign import split_dev
from src.labeling.schema import GOCLabel


def base(**kw):
    rec = dict(row_id=1, assignment="dev_A", goc_present="yes", annotator="TT",
               labeled_at="2026-10-16T00:00:00+00:00")
    rec.update(kw)
    return rec


@pytest.mark.parametrize("goc", ["yes", "no", "unclear"])
def test_valid_labels(goc):
    GOCLabel.model_validate(base(goc_present=goc))


@pytest.mark.parametrize("changes", [
    dict(goc_present="unsure"),       # stored as "unclear"
    dict(goc_present="maybe"),
    dict(annotator="T1"),
    dict(row_id=None),
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
