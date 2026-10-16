"""Label schema (pydantic). GOC is judged directly against the operational definition in
CLAUDE.md (decided 2026-10-16). Evidence is stored as character positions (evidence_start /
evidence_end into the unmodified NOTEEVENTS.TEXT), so label files never contain note text.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

NegativeReason = Literal["order_only", "consult_only", "planned_only", "clinician_only",
                         "no_serious_illness_context", "no_goc_content"]


class GOCLabel(BaseModel):
    row_id: int
    assignment: str
    goc_present: Literal["yes", "no", "unclear"]
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=0)
    negative_reason: NegativeReason | None = None  # optional, only when goc_present = no
    secondhand: bool = False                        # only when goc_present = yes
    annotator: str = Field(pattern=r"^[A-Za-z]{1,5}$")
    minutes_spent: float = Field(ge=0)
    labeled_at: str

    @model_validator(mode="after")
    def _rules(self) -> "GOCLabel":
        has_evidence = self.evidence_start is not None
        if has_evidence != (self.evidence_end is not None):
            raise ValueError("evidence_start and evidence_end must be set together")
        if has_evidence and self.evidence_end <= self.evidence_start:
            raise ValueError("evidence_end must be after evidence_start")
        if self.goc_present == "yes" and not has_evidence:
            raise ValueError("evidence is required when GOC = yes")
        if self.goc_present != "yes" and (has_evidence or self.secondhand):
            raise ValueError("evidence and secondhand apply only when GOC = yes")
        if self.goc_present != "no" and self.negative_reason is not None:
            raise ValueError("a reason applies only when GOC = no")
        return self
