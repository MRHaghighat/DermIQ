"""
core/fhir/builders.py
─────────────────────
Converts a Derm7pt metadata row → FHIR R4 resources.

Flow:
  derm7pt row (pandas Series)
      ↓  TerminologyMapper  (core/ontology/mapper.py)
      ↓  builds Pydantic schemas
      ↓  .to_fhir()
      ↓  FHIRClient.create()  →  HAPI server

Pydantic is used here for: construction-time validation before
sending to HAPI — any missing required field raises immediately.
"""

from __future__ import annotations

import uuid
import pandas as pd

from core.fhir.schemas import (
    PatientResource,
    ConditionResource,
    ObservationResource,
    MedicationRequestResource,
    CodeableConcept,
    Coding,
    Reference,
)
from core.ontology.mapper import TerminologyMapper
from config import SYSTEM_SNOMED, SYSTEM_ICD10, SYSTEM_LOINC


mapper = TerminologyMapper()


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_id() -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4())[:8]


def _ref(resource_type: str, resource_id: str, display: str | None = None) -> Reference:
    return Reference(reference=f"{resource_type}/{resource_id}", display=display)


# ── Patient ───────────────────────────────────────────────────────────────────

def build_patient(row: pd.Series) -> dict:
    """
    Build a FHIR Patient from a Derm7pt metadata row.
    Derm7pt has 'sex' and no real DOB — we synthesize a plausible birthDate.
    """
    gender_map = {"male": "male", "female": "female"}
    gender = gender_map.get(str(row.get("sex", "")).lower(), "unknown")

    patient = PatientResource(
        id=_new_id(),
        gender=gender,
        birthDate="1970",       # synthetic — Derm7pt has no real DOB
    )
    return patient.to_fhir()


# ── Condition ─────────────────────────────────────────────────────────────────

def build_condition(row: pd.Series, patient_id: str) -> dict:
    """
    Build a FHIR Condition encoding the diagnosis with SNOMED + ICD-10.
    """
    diagnosis = str(row.get("diagnosis", "miscellaneous"))
    term = mapper.get(diagnosis)

    # Primary coding: SNOMED CT
    snomed_coding = Coding(
        system=SYSTEM_SNOMED,
        code=term["snomed"]["conceptId"],
        display=term["snomed"]["display"],
    )

    # Secondary coding: ICD-10-CM
    icd_coding = Coding(
        system=SYSTEM_ICD10,
        code=term["icd10"]["code"],
        display=term["icd10"]["display"],
    )

    condition = ConditionResource(
        id=_new_id(),
        subject=_ref("Patient", patient_id),
        code=CodeableConcept(
            coding=[snomed_coding, icd_coding],
            text=diagnosis,
        ),
        note=[{"text": f"Derm7pt case #{row.get('case_num', 'unknown')}. "
                       f"Management: {row.get('management', 'unknown')}. "
                       f"Malignant: {term.get('malignant', 'unknown')}."}],
        recordedDate="2024-01-01",
    )
    return condition.to_fhir()


# ── Observations (7 dermoscopy criteria) ─────────────────────────────────────

# Maps Derm7pt column → (human label, LOINC code)
CRITERIA_CONFIG: dict[str, tuple[str, str]] = {
    "pigment_network":      ("Pigment network",      "44652-2"),
    "streaks":              ("Streaks",              "44652-2"),
    "pigmentation":         ("Pigmentation",         "44652-2"),
    "regression_structures":("Regression structures","44652-2"),
    "dots_and_globules":    ("Dots and globules",    "44652-2"),
    "blue_whitish_veil":    ("Blue-whitish veil",    "44652-2"),
    "vascular_structures":  ("Vascular structures",  "44652-2"),
}


def build_observations(row: pd.Series, patient_id: str) -> list[dict]:
    """
    Build one FHIR Observation per dermoscopy criterion + one for the
    7-point score.
    """
    observations = []

    for col, (label, loinc_code) in CRITERIA_CONFIG.items():
        value = str(row.get(col, "absent"))

        obs = ObservationResource(
            id=_new_id(),
            subject=_ref("Patient", patient_id),
            code=CodeableConcept(
                coding=[Coding(system=SYSTEM_LOINC, code=loinc_code, display=label)],
                text=label,
            ),
            valueCodeableConcept=CodeableConcept(
                coding=[Coding(
                    system="http://dermiq.local/derm7pt-values",
                    code=value.lower().replace(" ", "-"),
                    display=value,
                )],
                text=value,
            ),
        )
        observations.append(obs.to_fhir())

    # 7-point total score as integer observation
    score_val = row.get("seven_point_score")
    if score_val is not None:
        score_obs = ObservationResource(
            id=_new_id(),
            subject=_ref("Patient", patient_id),
            code=CodeableConcept(
                coding=[Coding(
                    system=SYSTEM_LOINC,
                    code="72135-7",
                    display="Seven-point checklist score",
                )],
                text="Seven-point checklist score",
            ),
            valueInteger=int(score_val),
        )
        observations.append(score_obs.to_fhir())

    return observations


# ── Full bundle builder ───────────────────────────────────────────────────────

def build_all(row: pd.Series) -> dict[str, dict | list]:
    """
    Build all FHIR resources for one Derm7pt case.
    Returns a dict with keys: patient, condition, observations.
    Call FHIRClient.create() on each to persist them.
    """
    patient = build_patient(row)
    patient_id = patient["id"]

    return {
        "patient": patient,
        "condition": build_condition(row, patient_id),
        "observations": build_observations(row, patient_id),
    }