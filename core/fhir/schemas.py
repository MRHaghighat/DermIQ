from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Shared building blocks ────────────────────────────────────────────────────
class Coding(BaseModel):
    system: str
    code: str
    display: str | None = None


class CodeableConcept(BaseModel):
    coding: list[Coding]
    text: str | None = None


class Reference(BaseModel):
    reference: str           # e.g. "Patient/abc123"
    display: str | None = None


# ── Patient ───────────────────────────────────────────────────────────────────

class PatientResource(BaseModel):
    resourceType: Literal["Patient"] = "Patient"
    id: str | None = None
    gender: Literal["male", "female", "other", "unknown"]
    birthDate: str | None = None          # YYYY or YYYY-MM-DD
    meta: dict = Field(default_factory=lambda: {
        "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
    })

    def to_fhir(self) -> dict:
        return self.model_dump(exclude_none=True)


# ── Condition (diagnosis) ─────────────────────────────────────────────────────

class ConditionResource(BaseModel):
    resourceType: Literal["Condition"] = "Condition"
    id: str | None = None
    subject: Reference
    code: CodeableConcept                 # SNOMED + ICD-10 codings
    clinicalStatus: CodeableConcept = Field(default_factory=lambda: CodeableConcept(
        coding=[Coding(
            system="http://terminology.hl7.org/CodeSystem/condition-clinical",
            code="active",
            display="Active"
        )]
    ))
    verificationStatus: CodeableConcept = Field(default_factory=lambda: CodeableConcept(
        coding=[Coding(
            system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
            code="confirmed",
            display="Confirmed"
        )]
    ))
    category: list[CodeableConcept] = Field(default_factory=lambda: [
        CodeableConcept(coding=[Coding(
            system="http://terminology.hl7.org/CodeSystem/condition-category",
            code="encounter-diagnosis",
            display="Encounter Diagnosis"
        )])
    ])
    note: list[dict] | None = None        # free text notes
    recordedDate: str | None = None

    def to_fhir(self) -> dict:
        return self.model_dump(exclude_none=True)


# ── Observation (dermoscopy criteria) ────────────────────────────────────────

class ObservationResource(BaseModel):
    resourceType: Literal["Observation"] = "Observation"
    id: str | None = None
    status: Literal["final", "preliminary"] = "final"
    subject: Reference
    code: CodeableConcept                 # LOINC code for the criterion
    valueCodeableConcept: CodeableConcept | None = None   # categorical value
    valueInteger: int | None = None                       # numeric value (score)
    category: list[CodeableConcept] = Field(default_factory=lambda: [
        CodeableConcept(coding=[Coding(
            system="http://terminology.hl7.org/CodeSystem/observation-category",
            code="imaging",
            display="Imaging"
        )])
    ])

    def to_fhir(self) -> dict:
        return self.model_dump(exclude_none=True)


# ── MedicationRequest (treatment suggestion) ──────────────────────────────────

class MedicationRequestResource(BaseModel):
    resourceType: Literal["MedicationRequest"] = "MedicationRequest"
    id: str | None = None
    status: Literal["active", "draft"] = "draft"
    intent: Literal["proposal", "plan", "order"] = "proposal"
    subject: Reference
    medicationCodeableConcept: CodeableConcept
    note: list[dict] | None = None        # RAG-generated rationale

    def to_fhir(self) -> dict:
        return self.model_dump(exclude_none=True)
