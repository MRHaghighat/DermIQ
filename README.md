# DermIQ — Dermatology Clinical Decision Support

> FHIR R4 · SNOMED CT · ICD-10 · LOINC · RAG · Ollama

A portfolio project demonstrating production-grade health informatics skills:
- **Data modeling** with HL7 FHIR R4 (HAPI server)
- **Medical ontologies** (SNOMED CT, ICD-10-CM, LOINC)
- **Computational reasoning** via RAG (PubMed + Ollama llama3.2)
- **Clinical decision support** on the Derm7pt dermoscopy dataset

---

## Architecture

```
Derm7pt dataset (1,011 cases)
    ↓
TerminologyMapper       — maps diagnosis → SNOMED + ICD-10 + LOINC
    ↓
FHIR Builders           — constructs Patient / Condition / Observation resources
    ↓
HAPI FHIR Server        — local Docker, REST API on :8080
    ↓
RAG Pipeline            — PubMed fetch → nomic-embed-text → llama3.2
    ↓
Streamlit Dashboard     — 4 pages
```

## Standards used

| Standard | Role in project |
|---|---|
| **HL7 FHIR R4** | Data interchange format — all resources are valid FHIR R4 |
| **SNOMED CT** | Primary clinical coding of diagnoses |
| **ICD-10-CM** | Secondary coding for billing/statistics |
| **LOINC** | Coding of dermoscopy observations |

## Setup

### 1. Start HAPI FHIR Server
```bash
cd docker
docker-compose up -d
# Wait ~60s, then verify: http://localhost:8080/fhir/metadata
```

### 2. Pull Ollama models
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Add Derm7pt data
Place the Derm7pt dataset in `data/derm7pt/`:
```
data/derm7pt/
├── meta.csv
└── images/   (dermoscopy images — optional for this demo)
```

### 5. Run the app
```bash
streamlit run app.py
```

---

## Project structure

```
dermiq/
├── docker/
│   └── docker-compose.yml       # HAPI FHIR R4 server
├── data/
│   ├── terminology_map.json     # SNOMED + ICD-10 + LOINC verified codes
│   └── derm7pt/meta.csv
├── core/
│   ├── fhir/
│   │   ├── client.py            # HAPI REST wrapper + retry logic
│   │   ├── builders.py          # Derm7pt row → FHIR resources
│   │   └── schemas.py           # Pydantic v2 FHIR models
│   ├── ontology/
│   │   ├── mapper.py            # Terminology lookup + Pydantic validation
│   │   └── graph.py             # networkx SNOMED hierarchy
│   └── rag/
│       ├── pubmed.py            # PubMed E-utilities fetcher
│       ├── embedder.py          # Ollama nomic-embed-text
│       └── retriever.py         # Full RAG pipeline → llama3.2
├── pages/
│   ├── 1_patient_card.py        # Load case → build → push to FHIR
│   ├── 2_ontology_explorer.py   # Interactive SNOMED graph (Plotly)
│   ├── 3_clinical_reasoning.py  # RAG treatment suggestions
│   └── 4_fhir_inspector.py      # Raw FHIR JSON browser
├── app.py                       # Streamlit entry point
├── config.py                    # All constants and env vars
└── requirements.txt
```

## Why Pydantic?

Pydantic v2 is used in two places with distinct purposes:

- **`core/fhir/schemas.py`** — validates FHIR resource structure *before* sending to HAPI. Catches missing required fields at construction time, not at HTTP-error time.
- **`core/ontology/mapper.py`** — validates every entry in `terminology_map.json` at startup. A malformed terminology entry fails loudly on load, not silently mid-request.

## Design decisions worth explaining in interviews

**Why local HAPI over public sandbox?**
Full infrastructure ownership — demonstrates containerization skills and produces stable, reproducible demos.

**Why Ollama over OpenAI?**
Zero external dependencies, fully reproducible, no API cost. `nomic-embed-text` (768-dim) is well-suited for medical text similarity.

**Why manual terminology_map.json over automatic lookup?**
For 20 diagnoses, manual curation + source citation is more defensible than automated mapping. Shows understanding of the standards, not just their APIs.

**LOINC gap for dermoscopy criteria**
Dermoscopy-specific observations (pigment network, streaks, etc.) lack standard LOINC codes. The project uses LOINC `44652-2` as a base code with `Observation.code.text` for specificity — a real-world pattern used when terminology gaps exist.
