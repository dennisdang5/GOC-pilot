"""Label schema (pydantic). Matches CLAUDE.md, except evidence is stored as character positions
(evidence_start / evidence_end into the unmodified NOTEEVENTS.TEXT) so label files never
contain note text and can be sent back safely.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.labeling.derive import derive_goc

YesNoUnclear = Literal["yes", "no", "unclear"]
Participant = Literal["patient", "family", "surrogate", "clinician_only", "unclear"]
NegativeReason = Literal["order_only", "consult_only", "planned_only", "clinician_only",
                         "no_serious_illness_context", "no_goc_content"]
GocType = Literal["family_meeting", "code_status", "prognosis_disclosure",
                  "hospice_transition", "acp_general", "other"]


class GOCLabel(BaseModel):
    row_id: int
    assignment: str
    interaction_documented: YesNoUnclear
    participants: list[Participant] = Field(min_length=1)
    content_relevant: YesNoUnclear
    goc_present: YesNoUnclear
    evidence_start: int | None = Field(default=None, ge=0)
    evidence_end: int | None = Field(default=None, ge=0)
    negative_reason: NegativeReason | None = None
    goc_type: GocType | None = None
    secondhand: bool = False
    anticipated: bool = False
    annotator: str = Field(pattern=r"^[A-Za-z]{1,5}$")
    confidence: int = Field(ge=1, le=5)  # 1 = guess, 5 = certain
    minutes_spent: float = Field(ge=0)
    labeled_at: str

    @model_validator(mode="after")
    def _rules(self) -> "GOCLabel":
        parts = set(self.participants)
        if "clinician_only" in parts and len(parts) > 1:
            raise ValueError("clinician_only cannot be combined with other participants")
        if self.goc_present != derive_goc(self.interaction_documented, self.participants,
                                          self.content_relevant):
            raise ValueError("goc_present does not match the three tests")
        if (self.evidence_start is None) != (self.evidence_end is None):
            raise ValueError("evidence_start and evidence_end must be set together")
        if self.evidence_start is not None and self.evidence_end <= self.evidence_start:
            raise ValueError("evidence_end must be after evidence_start")
        if self.goc_present == "yes":
            if self.evidence_start is None:
                raise ValueError("evidence is required when goc_present = yes")
            if self.goc_type is None:
                raise ValueError("goc_type is required when goc_present = yes")
            if self.negative_reason is not None:
                raise ValueError("negative_reason must be empty when goc_present = yes")
        if self.goc_present == "no":
            if self.negative_reason is None:
                raise ValueError("negative_reason is required when goc_present = no")
            if self.goc_type is not None:
                raise ValueError("goc_type must be empty when goc_present = no")
        return self
