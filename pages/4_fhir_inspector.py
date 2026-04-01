"""
pages/4_fhir_inspector.py
──────────────────────────
Query the live HAPI FHIR server and inspect raw FHIR R4 JSON.
The "show the recruiter" page.
"""

import streamlit as st
from core.fhir.client import FHIRClient, FHIRError

st.set_page_config(page_title="FHIR Inspector — DermIQ", layout="wide")
st.title("FHIR Inspector")
st.caption("Query the live HAPI FHIR R4 server and inspect raw resources.")

@st.cache_resource
def get_client():
    return FHIRClient()

client = get_client()

# ── Server status ─────────────────────────────────────────────────────────────
if client.ping():
    st.success("HAPI FHIR Server — Connected (http://localhost:8080/fhir)")
else:
    st.error("HAPI FHIR Server — Offline. Start with: `docker-compose up -d`")
    st.stop()

st.divider()

# ── Resource browser ──────────────────────────────────────────────────────────
st.subheader("Browse Resources")
col1, col2 = st.columns([1, 2])

with col1:
    resource_type = st.selectbox(
        "Resource type",
        ["Patient", "Condition", "Observation", "MedicationRequest"],
    )

with col2:
    resource_id = st.text_input(
        "Resource ID (leave blank to list all)",
        placeholder="e.g. abc12345",
    )

if st.button("Fetch", type="primary"):
    try:
        if resource_id.strip():
            result = client.read(resource_type, resource_id.strip())
            st.json(result)
        else:
            results = client.search(resource_type, {})
            st.info(f"Found {len(results)} {resource_type} resources")
            for r in results[:10]:
                with st.expander(f"{resource_type}/{r.get('id', '?')}"):
                    st.json(r)
    except FHIRError as e:
        st.error(str(e))

st.divider()

# ── Use last pushed patient ───────────────────────────────────────────────────
if "last_patient_id" in st.session_state:
    pid = st.session_state["last_patient_id"]
    st.subheader(f"Last pushed: Patient/{pid}")

    if st.button("Load Patient + related resources"):
        try:
            patient = client.read("Patient", pid)
            st.markdown("**Patient**")
            st.json(patient)

            conditions = client.search("Condition", {"subject": f"Patient/{pid}"})
            st.markdown(f"**Conditions ({len(conditions)})**")
            for c in conditions:
                st.json(c)

            observations = client.search("Observation", {"subject": f"Patient/{pid}"})
            st.markdown(f"**Observations ({len(observations)})**")
            for o in observations:
                st.json(o)

        except FHIRError as e:
            st.error(str(e))

# ── Raw query ─────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Custom Search Parameters")
raw_params = st.text_input(
    "Search params (key=value, comma-separated)",
    placeholder="e.g. subject=Patient/abc123, status=final",
)
raw_type = st.selectbox("Resource type", ["Observation", "Condition", "Patient"], key="raw_rt")

if st.button("Run custom search"):
    try:
        params = {}
        for pair in raw_params.split(","):
            if "=" in pair:
                k, v = pair.strip().split("=", 1)
                params[k.strip()] = v.strip()
        results = client.search(raw_type, params)
        st.info(f"{len(results)} results")
        for r in results:
            st.json(r)
    except Exception as e:
        st.error(str(e))
