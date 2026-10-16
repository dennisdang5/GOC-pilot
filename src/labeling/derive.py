"""Pure helpers for labeling: derive goc_present and locate evidence spans.

No I/O. Safe to unit-test on synthetic strings.
"""

SURROGATE_PARTIES = {"patient", "family", "surrogate"}


def participants_test(participants: list[str]) -> str:
    """yes if the patient/family/surrogate took part, no if clinicians only, else unclear."""
    if SURROGATE_PARTIES & set(participants):
        return "yes"
    if participants == ["clinician_only"]:
        return "no"
    return "unclear"


def derive_goc(interaction: str, participants: list[str], content: str) -> str:
    """goc_present from the three tests: any 'no' -> no; all 'yes' -> yes; else unclear."""
    tests = [interaction, participants_test(participants), content]
    if "no" in tests:
        return "no"
    if all(t == "yes" for t in tests):
        return "yes"
    return "unclear"


def _normalize(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace runs to one space; return normalized text and norm->orig index map."""
    out, idx = [], []
    in_ws = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not in_ws:
                out.append(" ")
                idx.append(i)
            in_ws = True
        else:
            out.append(ch)
            idx.append(i)
            in_ws = False
    return "".join(out), idx


def find_evidence(text: str, pasted: str) -> tuple[int, int] | None:
    """Locate `pasted` in `text`, whitespace-normalized and case-sensitive.

    Returns (start, end) character positions in the original text, or None if absent.
    """
    needle = " ".join(pasted.split())
    if not needle:
        return None
    norm, idx = _normalize(text)
    pos = norm.find(needle)
    if pos < 0:
        return None
    return idx[pos], idx[pos + len(needle) - 1] + 1
