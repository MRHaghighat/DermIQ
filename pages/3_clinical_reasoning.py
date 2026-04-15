import streamlit as st
from core.ontology.mapper import TerminologyMapper
from core.rag.retriever import run_rag

st.set_page_config(page_title="Clinical Reasoning — DermIQ", layout="wide")
st.title("Clinical Reasoning")
st.caption("Evidence-based treatment suggestions via PubMed RAG + Ollama llama3.2.")

@st.cache_resource
def get_mapper():
    return TerminologyMapper()

mapper = get_mapper()

# Input
st.subheader("Select Diagnosis")
col1, col2 = st.columns([1, 2])

with col1:
    diagnosis = st.selectbox("Diagnosis", mapper.all_labels)

term = mapper.get(diagnosis)
snomed_display = term["snomed"]["display"]

with col2:
    st.markdown("**Coding**")
    st.write(f"SNOMED: `{term['snomed']['conceptId']}` — {snomed_display}")
    st.write(f"ICD-10: `{term['icd10']['code']}` — {term['icd10']['display']}")
    malignant = term["malignant"]
    if malignant:
        st.error("Malignant diagnosis — handle with urgency")
    elif malignant is False:
        st.success("Benign diagnosis")

st.divider()

# Clinical question
custom_q = st.text_area(
    "Clinical question (optional — leave blank for default treatment query)",
    placeholder=f"e.g. What are first-line treatments for {snomed_display} in elderly patients?",
    height=80,
)

# Run RAG
    question = custom_q.strip() or None

    with st.spinner("Fetching PubMed abstracts..."):
        # Run full RAG pipeline
        result = run_rag(
            diagnosis=diagnosis,
            snomed_display=snomed_display,
            clinical_question=question,
        )

    st.divider()
    st.subheader("Clinical Summary")
    st.info(f"Based on {result['abstracts_used']} PubMed abstracts — top {len(result['sources'])} retrieved")

    st.markdown(result["summary"])

    # Sources
    st.divider()
    st.subheader("Sources")
    for i, src in enumerate(result["sources"], 1):
        with st.expander(f"[{i}] {src['title'][:80]}... ({src['year']})"):
            st.write(f"**PMID:** {src['pmid']}")
            st.write(f"**URL:** {src['url']}")
            st.markdown(f"[Open in PubMed]({src['url']})")

    # Disclaimer
    st.divider()
    st.warning(
        "This output is for research and portfolio demonstration purposes only. "
        "Not intended for clinical decision-making."
    )
