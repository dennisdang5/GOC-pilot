"""Pure helper for labeling: locate a pasted evidence quote in the note.

No I/O. Safe to unit-test on synthetic strings.
"""


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
