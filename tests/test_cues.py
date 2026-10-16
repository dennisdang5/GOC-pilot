"""Screening cue patterns: compile, and hit/miss on hand-written synthetic sentences."""

import re

import pytest

from src.sampling.cues import CUE_PATTERNS, PROBE_PATTERNS


def cue_hits(text: str) -> set[str]:
    return {n for n, p in CUE_PATTERNS.items() if re.search(p, text, re.IGNORECASE)}


def test_patterns_compile_and_names_disjoint():
    for p in {**CUE_PATTERNS, **PROBE_PATTERNS}.values():
        re.compile(p)
    assert not set(CUE_PATTERNS) & set(PROBE_PATTERNS)


@pytest.mark.parametrize("text, expected", [
    ("Family meeting held with daughter today.", "family_meeting"),
    ("Discussed goals of care with wife.", "goals_of_care"),
    ("We discussed code status with the patient.", "discussed_code_status"),
    ("DNR was discussed with son at bedside.", "discussed_code_status"),
    ("Transitioned to comfort measures only.", "comfort_care"),
    ("Being at home is important to her.", "important_to"),
    ("He wants to be able to walk his dog again.", "wants_to_be_able_to"),
    ("Patient would not want intubation.", "would_not_want"),
    ("Spoke with HCP by phone.", "health_care_proxy"),
    ("Updated pt's health care proxy on plan.", "health_care_proxy"),
    ("No family meeting held yet.", "family_meeting"),  # negation ignored by design
])
def test_cue_hits(text, expected):
    assert expected in cue_hits(text)


@pytest.mark.parametrize("text", [
    "Code status: Full code",
    "Code: DNR/DNI",
    "Pt resting comfortably, vitals stable.",
    "Hopeful for extubation tomorrow.",
    "HCP is wife.",
    "Daughter (HCP) at bedside.",
    "HCP: son",
])
def test_template_and_plain_lines_are_not_cues(text):
    assert cue_hits(text) == set()


def probe(name: str, text: str) -> bool:
    return re.search(PROBE_PATTERNS[name], text, re.IGNORECASE) is not None


@pytest.mark.parametrize("text, heading, nonheading", [
    ("HCP: daughter", True, False),
    ("HCP : son", True, False),
    ("Spoke with HCP by phone.", False, True),
    ("Called HCP", False, True),
    ("Health care proxy: wife", True, False),
])
def test_hcp_heading_split(text, heading, nonheading):
    assert probe("probe_hcp_heading", text) is heading
    assert probe("probe_hcp_nonheading", text) is nonheading
