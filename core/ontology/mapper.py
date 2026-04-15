from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from config import TERMINOLOGY_MAP_PATH

logger = logging.getLogger(__name__)

# Pydantic models for terminology entries
class SnomedEntry(BaseModel):
    conceptId: str
    fsn: str
    display: str
    system: str

class Icd10Entry(BaseModel):
    code: str
    display: str
    system: str

class LoincEntry(BaseModel):
    code: str
    display: str
    system: str

class DiagnosisEntry(BaseModel):
    derm7pt_label: str
    case_count: int
    malignant: bool | None
    snomed: SnomedEntry
    icd10: Icd10Entry
    loinc_observation: LoincEntry
    hierarchy: list[str]

# Mapper
class TerminologyMapper:
    _FALLBACK_LABEL = "miscellaneous"

    def __init__(self, path: Path = TERMINOLOGY_MAP_PATH):
        self._path = path
        self._entries: dict[str, DiagnosisEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(
                f"terminology_map.json not found at {self._path}. "
                "Copy it to data/terminology_map.json."
            )
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for label, data in raw["diagnoses"].items():
            try:
                self._entries[label] = DiagnosisEntry(**data)
            except Exception as e:
                logger.warning("Skipping invalid entry '%s': %s", label, e)
        logger.info("Loaded %d terminology entries", len(self._entries))

    def get(self, label: str) -> dict:
        entry = self._entries.get(label) or self._entries.get(self._FALLBACK_LABEL)
        if entry is None:
            raise KeyError(f"Label '{label}' not found and no fallback available.")
        return entry.model_dump()

    def snomed_id(self, label: str) -> str:
        return self.get(label)["snomed"]["conceptId"]

    def icd10_code(self, label: str) -> str:
        return self.get(label)["icd10"]["code"]

    def loinc_code(self, label: str) -> str:
        return self.get(label)["loinc_observation"]["code"]

    def is_malignant(self, label: str) -> bool | None:
        return self.get(label)["malignant"]

    def hierarchy(self, label: str) -> list[str]:
        return self.get(label)["hierarchy"]

    @property
    def all_labels(self) -> list[str]:
        return list(self._entries.keys())

    @property
    def all_entries(self) -> dict[str, dict]:
        return {k: v.model_dump() for k, v in self._entries.items()}
