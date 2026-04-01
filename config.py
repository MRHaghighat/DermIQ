"""
DermIQ — Central configuration
All environment variables and constants live here.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TERMINOLOGY_MAP_PATH = DATA_DIR / "terminology_map.json"
DERM7PT_META_PATH = DATA_DIR / "derm7pt" / "meta.csv"
DERM7PT_IMAGES_DIR = DATA_DIR / "derm7pt" / "images"
# ساختار واقعی Derm7pt: images/NEL/NEL025.JPG (clinic و derm پیش هم)
# مسیر تصویر = DERM7PT_IMAGES_DIR / folder / filename
# مثال: clinic col در meta.csv = "NEL/NEL025.JPG"

# ── HAPI FHIR Server ─────────────────────────────────────────────────────────
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://localhost:8080/fhir")
FHIR_TIMEOUT = 30  # seconds

# ── Ollama ───────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ── PubMed ───────────────────────────────────────────────────────────────────
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_MAX_RESULTS = 15
PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "dermiq@example.com")  # NCBI asks for email

# ── RAG ──────────────────────────────────────────────────────────────────────
RAG_TOP_K = 5                    # top-k abstracts to retrieve
RAG_CHUNK_SIZE = 512             # characters per chunk
RAG_SIMILARITY_THRESHOLD = 0.3   # cosine similarity cutoff

# ── FHIR Coding Systems ──────────────────────────────────────────────────────
SYSTEM_SNOMED = "http://snomed.info/sct"
SYSTEM_ICD10  = "http://hl7.org/fhir/sid/icd-10-cm"
SYSTEM_LOINC  = "http://loinc.org"

# ── App ──────────────────────────────────────────────────────────────────────
APP_TITLE = "DermIQ"
APP_SUBTITLE = "Dermatology Clinical Decision Support — FHIR R4 + Ontology"
APP_VERSION = "1.0.0"