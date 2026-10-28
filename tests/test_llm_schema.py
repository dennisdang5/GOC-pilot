"""LLM output schema and evidence-span check (synthetic strings only)."""

import pytest
from pydantic import ValidationError

from src.llm.schema import LLMOutput
from src.llm.validate import span_verified

NOTE = ("Met with patient's daughter [**Name (NI) 123**] today.\n"
        "Discussed   prognosis and\nher father's wishes; she agrees with comfort care.")


@pytest.mark.parametrize("rec", [
    dict(evidence_span="Discussed prognosis", goc_present="yes"),
    dict(evidence_span=None, goc_present="no"),
])
def test_valid_output(rec):
    LLMOutput.model_validate(rec)


@pytest.mark.parametrize("rec", [
    dict(evidence_span=None, goc_present="unclear"),   # models answer yes / no only
    dict(evidence_span=None, goc_present="YES"),
    dict(goc_present="yes"),                           # span key is required (may be null)
    dict(evidence_span=None, goc_present="no", reason="x"),
])
def test_invalid_output(rec):
    with pytest.raises(ValidationError):
        LLMOutput.model_validate(rec)


def test_schema_field_order():
    # quote first, then decide
    assert list(LLMOutput.model_json_schema()["properties"]) == ["evidence_span", "goc_present"]


@pytest.mark.parametrize("span, expected", [
    ("Discussed prognosis and her father's wishes", True),     # whitespace differs
    ("daughter [**Name (NI) 123**] today", True),              # placeholder kept verbatim
    ("discussed prognosis", False),                            # case-sensitive
    ("Discussed prognosis with the patient", False),           # not in note
    ("daughter [** **] today", False),                         # placeholder not rewritten
    (None, None),
    ("   ", None),
])
def test_span_verified(span, expected):
    assert span_verified(span, NOTE) is expected
