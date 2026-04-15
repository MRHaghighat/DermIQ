import streamlit as st
import pandas as pd
import json

from config import DERM7PT_META_PATH, DERM7PT_IMAGES_DIR
from core.fhir.client import FHIRClient, FHIRError
from core.fhir.builders import build_all
from core.ontology.mapper import TerminologyMapper

st.set_page_config(page_title="Patient Card — DermIQ", layout="wide")
st.title("Patient Card")
st.caption("Load a Derm7pt case, encode it as FHIR R4, and push to HAPI server.")

# Load data
@st.cache_data
def load_meta() -> pd.DataFrame:
    return pd.read_csv(DERM7PT_META_PATH)

@st.cache_resource
def get_mapper() -> TerminologyMapper:
    return TerminologyMapper()

@st.cache_resource
def get_client() -> FHIRClient:
    return FHIRClient()

try:
    df = load_meta()
    mapper = get_mapper()
    client = get_client()
except Exception as e:
    st.error(f"Initialization error: {e}")
    st.stop()

# Case selector
st.subheader("Select Case")
col1, col2 = st.columns([1, 2])

with col1:
    case_num = st.selectbox(
        "Case number",
        options=df["case_num"].tolist(),
        format_func=lambda x: f"Case #{x}",
    )

row = df[df["case_num"] == case_num].iloc[0]
diagnosis = row["diagnosis"]
term = mapper.get(diagnosis)

with col2:
    malignant = term.get("malignant")
    badge = "🔴 Malignant" if malignant else ("🟡 Unknown" if malignant is None else "🟢 Benign")
    st.metric("Diagnosis", diagnosis)
    st.caption(badge)

st.divider()

# Images
img_col1, img_col2 = st.columns(2)
with img_col1:
    clinic_path = row.get("clinic", "")
    if clinic_path and str(clinic_path) != "nan":
        full_path = DERM7PT_IMAGES_DIR / clinic_path
        if full_path.exists():
            st.image(str(full_path), caption="Clinical image", use_column_width=True)
        else:
            st.info(f"Clinical image not found: {clinic_path}")
with img_col2:
    derm_path = row.get("derm", "")
    if derm_path and str(derm_path) != "nan":
        full_path = DERM7PT_IMAGES_DIR / derm_path
        if full_path.exists():
            st.image(str(full_path), caption="Dermoscopy image", use_column_width=True)
        else:
            st.info(f"Dermoscopy image not found: {derm_path}")

st.divider()

# Display case details
st.subheader("Clinical Data")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("**Patient**")
    st.write(f"Sex: {row.get('sex', 'unknown')}")
    st.write(f"Location: {row.get('location', 'unknown')}")
    st.write(f"Elevation: {row.get('elevation', 'unknown')}")

with col_b:
    st.markdown("**Dermoscopy (7 criteria)**")
    criteria = [
        "pigment_network", "streaks", "pigmentation",
        "regression_structures", "dots_and_globules",
        "blue_whitish_veil", "vascular_structures",
    ]
    for c in criteria:
        val = row.get(c, "—")
        st.write(f"{c.replace('_', ' ').title()}: `{val}`")

with col_c:
    st.markdown("**Coding**")
    st.write(f"SNOMED: `{term['snomed']['conceptId']}`")
    st.caption(term['snomed']['display'])
    st.write(f"ICD-10: `{term['icd10']['code']}`")
    st.caption(term['icd10']['display'])
    st.write(f"Seven-point score: `{row.get('seven_point_score', '—')}`")
    st.write(f"Management: `{row.get('management', '—')}`")

st.divider()

# Build & Push to FHIR
st.subheader("FHIR R4 Resources")

if st.button("Build & Push to HAPI FHIR Server", type="primary"):
    with st.spinner("Building FHIR resources..."):
        resources = build_all(row)

    st.success(f"Built: 1 Patient + 1 Condition + {len(resources['observations'])} Observations")

    if client.ping():
        with st.spinner("Pushing to HAPI..."):
            try:
                patient_id = client.create("Patient", resources["patient"])

                resources["condition"]["subject"]["reference"] = f"Patient/{patient_id}"
                for obs in resources["observations"]:
                    obs["subject"]["reference"] = f"Patient/{patient_id}"

                condition_id = client.create("Condition", resources["condition"])
                obs_ids = [client.create("Observation", obs) for obs in resources["observations"]]

                st.success(
                    f"Pushed to FHIR:\n"
                    f"- Patient/{patient_id}\n"
                    f"- Condition/{condition_id}\n"
                    f"- {len(obs_ids)} Observations"
                )
                st.session_state["last_patient_id"] = patient_id
                st.session_state["last_resources"] = resources
            except FHIRError as e:
                st.error(f"FHIR push failed: {e}")
                st.code(str(e), language="text")
    else:
        st.warning("HAPI server offline — showing resources locally only.")
        st.session_state["last_resources"] = resources

# Show built JSON
if "last_resources" in st.session_state:
    with st.expander("View built FHIR JSON"):
        tab1, tab2, tab3 = st.tabs(["Patient", "Condition", "Observations"])
        r = st.session_state["last_resources"]
        with tab1:
            st.json(r["patient"])
        with tab2:
            st.json(r["condition"])
        with tab3:
            for obs in r["observations"]:
                st.json(obs)
