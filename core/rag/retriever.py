from __future__ import annotations

import logging
import requests

from core.rag.pubmed import fetch_abstracts
from core.rag.embedder import embed_texts, top_k_indices
from config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, RAG_TOP_K, RAG_CHUNK_SIZE

logger = logging.getLogger(__name__)

GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"


def _generate(prompt: str, system: str) -> str:
    payload = {
        "model": OLLAMA_LLM_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.2,     # low temp for clinical accuracy
            "num_predict": 600,
        },
    }
    try:
        resp = requests.post(GENERATE_URL, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        logger.error("Ollama generation failed: %s", e)
        return f"[Generation failed: {e}]"


def _build_context(abstracts: list[dict], top_indices: list[int]) -> str:
    parts = []
    for rank, idx in enumerate(top_indices, 1):
        a = abstracts[idx]
        parts.append(
            f"[{rank}] {a['title']} ({a['year']})\n"
            f"PMID: {a['pmid']} | URL: {a['url']}\n"
            f"{a['abstract'][:RAG_CHUNK_SIZE]}"
        )
    return "\n\n---\n\n".join(parts)


def run_rag(
    diagnosis: str, #Derm7pt label
    snomed_display: str, #SNOMED FSN display name
    clinical_question: str | None = None, # Optional specific question (default: treatment)
) -> dict:

    if clinical_question is None:
        clinical_question = (
            f"What are the current evidence-based treatment options "
            f"and management guidelines for {snomed_display}?"
        )

    # PubMed abstracts
    logger.info("RAG: fetching PubMed abstracts for '%s'", diagnosis)
    abstracts = fetch_abstracts(diagnosis, snomed_display)

    if not abstracts:
        return {
            "summary": f"No PubMed abstracts found for '{snomed_display}'. "
                       "Unable to generate evidence-based summary.",
            "sources": [],
            "abstracts_used": 0,
            "query_used": diagnosis,
        }

    #  Embed corpus + query
    logger.info("RAG: embedding %d abstracts", len(abstracts))
    corpus_texts = [a["text"] for a in abstracts]
    corpus_vecs  = embed_texts(corpus_texts)

    query_vec = embed_texts([clinical_question])[0]

    # Retrieve top-k
    k = min(RAG_TOP_K, len(abstracts))
    top_idx = top_k_indices(query_vec, corpus_vecs, k)
    context = _build_context(abstracts, top_idx)

    # clinical summary
    system_prompt = (
        "You are a clinical dermatology assistant. "
        "Your role is to summarize medical evidence and suggest treatment approaches "
        "based ONLY on the provided PubMed abstracts. "
        "Always cite sources by their PMID number [PMID: XXXXX]. "
        "Be concise, clinically precise, and note any uncertainty. "
        "Do NOT invent information not present in the abstracts."
    )

    user_prompt = (
        f"Diagnosis: {snomed_display}\n\n"
        f"Clinical question: {clinical_question}\n\n"
        f"Relevant PubMed abstracts:\n\n{context}\n\n"
        f"Please provide:\n"
        f"1. A 2-3 sentence clinical summary of this condition\n"
        f"2. Evidence-based treatment options (cite PMIDs)\n"
        f"3. Key management considerations\n"
        f"4. Confidence level (high/medium/low) based on evidence quality"
    )

    logger.info("RAG: generating summary with %s", OLLAMA_LLM_MODEL)
    summary = _generate(user_prompt, system_prompt)

    # Collect cited sources
    sources = [
        {
            "pmid": abstracts[i]["pmid"],
            "title": abstracts[i]["title"],
            "url": abstracts[i]["url"],
            "year": abstracts[i]["year"],
        }
        for i in top_idx
    ]

    return {
        "summary": summary,
        "sources": sources,
        "abstracts_used": len(abstracts),
        "query_used": clinical_question,
    }
