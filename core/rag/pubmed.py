from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import PUBMED_BASE_URL, PUBMED_EMAIL, PUBMED_MAX_RESULTS

logger = logging.getLogger(__name__)


def _build_query(diagnosis: str, snomed_display: str) -> str:
    terms = [
        f'"{snomed_display}"[Title/Abstract]',
        '"dermoscopy"[Title/Abstract]',
        '"treatment"[Title/Abstract]',
        '"skin"[Title/Abstract]',
    ]
    return " AND ".join(terms[:2]) + " OR " + f'"{snomed_display}"[Title/Abstract]'


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _esearch(query: str, max_results: int) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "tool": "dermiq",
        "email": PUBMED_EMAIL,
    }
    resp = requests.get(f"{PUBMED_BASE_URL}/esearch.fcgi", params=params, timeout=15)
    resp.raise_for_status()
    ids = resp.json().get("esearchresult", {}).get("idlist", [])
    logger.info("PubMed esearch returned %d PMIDs for query: %s", len(ids), query[:60])
    return ids


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _efetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
        "tool": "dermiq",
        "email": PUBMED_EMAIL,
    }
    resp = requests.get(f"{PUBMED_BASE_URL}/efetch.fcgi", params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    articles = []

    for article in root.findall(".//PubmedArticle"):
        try:
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//AbstractText")
            year_el = article.find(".//PubDate/Year")

            pmid = pmid_el.text if pmid_el is not None else "unknown"
            title = title_el.text if title_el is not None else ""
            abstract = abstract_el.text if abstract_el is not None else ""
            year = year_el.text if year_el is not None else ""

            if abstract:
                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "text": f"{title}. {abstract}",   # combined for embedding
                })
        except Exception as e:
            logger.warning("Failed to parse article: %s", e)

    logger.info("Fetched %d abstracts", len(articles))
    return articles


def fetch_abstracts(
    diagnosis: str,
    snomed_display: str,
    max_results: int = PUBMED_MAX_RESULTS, # How many abstracts to fetch
) -> list[dict]:

    query = _build_query(diagnosis, snomed_display)
    pmids = _esearch(query, max_results)
    if not pmids:
        logger.warning("No PubMed results for: %s", diagnosis)
        return []

    time.sleep(0.34)   # NCBI rate limit: max 3 requests/sec
    return _efetch(pmids)
