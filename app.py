"""
app.py — DermIQ Streamlit entry point
Run: streamlit run app.py
"""

import streamlit as st
from config import APP_TITLE, APP_SUBTITLE, APP_VERSION
from core.fhir.client import FHIRClient

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.divider()

    # FHIR server health check
    client = FHIRClient()
    fhir_ok = client.ping()
    status_color = "green" if fhir_ok else "red"
    status_text  = "Connected" if fhir_ok else "Offline"
    st.markdown(
        f"**FHIR Server:** :{status_color}[{status_text}]"
    )
    st.caption(f"v{APP_VERSION}")

# ── Home page ─────────────────────────────────────────────────────────────────
st.title(f"{APP_TITLE} — Clinical Decision Support")
st.markdown(f"*{APP_SUBTITLE}*")
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Dataset", "Derm7pt", "1,011 cases")
with col2:
    st.metric("FHIR Resources", "4 types", "Patient · Condition · Observation · MedRequest")
with col3:
    st.metric("Standards", "3", "SNOMED CT · ICD-10 · LOINC")

st.info(
    "Navigate using the sidebar pages:\n"
    "- **Patient Card** — load a Derm7pt case and push to FHIR\n"
    "- **Ontology Explorer** — browse the SNOMED disease hierarchy\n"
    "- **Clinical Reasoning** — RAG-powered treatment suggestions\n"
    "- **FHIR Inspector** — inspect raw FHIR JSON"
)
