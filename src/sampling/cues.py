"""Screening cue phrases for sampling strata (cues present / cues missing).

A sampling tool only -- never a method under evaluation; src/eval/ must not import it.
Patterns are matched case-insensitively (DuckDB/RE2 and Python `re` share this syntax).
Negation is deliberately ignored: "no family meeting" still counts as a cue.

DRAFT: finalize after reviewing `python -m src.sampling.cue_frequency`.
"""

# name -> regex. A note matching any of these is "cues present".
CUE_PATTERNS: dict[str, str] = {
    # discussion / meeting
    "family_meeting": r"family meeting",
    "goals_of_care": r"goals? of care|\bgoc\b",
    "discussed_code_status": r"discuss\w* (code status|dnr|dni|prognosis|goals)"
                             r"|(code status|dnr|dni) (was |were )?discussed",
    "end_of_life": r"end of life",
    "quality_of_life": r"quality of life",
    # transitions
    "comfort_care": r"comfort (care|measures)|\bcmo\b",
    "hospice": r"hospice",
    "palliative": r"palliative",
    "withdraw_care": r"withdraw\w* (of )?(care|support)",
    "redirect_care": r"redirect\w* (of )?care",
    # documents / surrogates
    # talk verbs only (decided 2026-10-16): bare HCP mostly just names the proxy
    "health_care_proxy": r"(spoke|speak|talked|discuss\w*|met|meeting|call\w*|updat\w*|contact\w*)"
                         r"\s+(with\s+|to\s+)?(the\s+|pt.?s\s+|patient.?s\s+|his\s+|her\s+)?"
                         r"(health ?care proxy|\bhcp\b)",
    "advance_directive": r"advance directive",
    "molst_polst": r"\b(molst|polst)\b",
    # direction-neutral value language (required by CLAUDE.md)
    "important_to": r"important to (him|her|them)",
    "matters_most": r"matters most",
    "hopes_to": r"hopes to",
    "wants_to_be_able_to": r"wants to be able to",
    "would_not_want": r"would not want",
    "wishes": r"\bwishes\b",
}

# Measured by cue_frequency.py but NOT cues: likely template headings ("Code status: Full code").
PROBE_PATTERNS: dict[str, str] = {
    "probe_code_status": r"code status",
    "probe_dnr": r"\bdnr\b",
    "probe_dni": r"\bdni\b",
    "probe_full_code": r"full code",
    # heading form ("X:") vs. any non-heading use, to spot form fields
    "probe_hcp_heading": r"(health ?care proxy|\bhcp\b)\s*:",
    "probe_hcp_nonheading": r"(health ?care proxy|\bhcp\b)\s*([^:\s]|$)",
    "probe_family_meeting_heading": r"family meeting\s*:",
    "probe_family_meeting_nonheading": r"family meeting\s*([^:\s]|$)",
    "probe_goc_heading": r"(goals? of care|\bgoc\b)\s*:",
    "probe_goc_nonheading": r"(goals? of care|\bgoc\b)\s*([^:\s]|$)",
    "probe_code_status_heading": r"code status\s*:",
}
