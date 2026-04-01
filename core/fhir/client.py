"""
core/fhir/client.py
───────────────────
Thin wrapper around HAPI FHIR REST API.
Handles HTTP, error mapping, and retry logic.

Pydantic is used here for: response validation of FHIR OperationOutcome errors.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.util.retry import Retry

from config import FHIR_BASE_URL, FHIR_TIMEOUT

logger = logging.getLogger(__name__)


class FHIRError(Exception):
    """Raised when HAPI returns a non-2xx response."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"FHIR {status_code}: {message}")


def _build_session() -> requests.Session:
    """Session with connection pooling and automatic retry on 5xx."""
    session = requests.Session()
    retry_policy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_policy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    })
    return session


class FHIRClient:
    """
    CRUD operations against a HAPI FHIR R4 server.

    Usage:
        client = FHIRClient()
        patient_id = client.create("Patient", patient_dict)
        resource   = client.read("Patient", patient_id)
        results    = client.search("Condition", {"subject": f"Patient/{patient_id}"})
        client.delete("Patient", patient_id)
    """

    def __init__(self, base_url: str = FHIR_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._session = _build_session()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _url(self, resource_type: str, resource_id: str | None = None) -> str:
        if resource_id:
            return f"{self.base_url}/{resource_type}/{resource_id}"
        return f"{self.base_url}/{resource_type}"

    def _raise_for_fhir_error(self, response: requests.Response) -> None:
        if response.status_code >= 400:
            try:
                outcome = response.json()
                msg = outcome.get("issue", [{}])[0].get("diagnostics", response.text)
            except Exception:
                msg = response.text
            raise FHIRError(response.status_code, msg)

    # ── public API ────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def create(self, resource_type: str, resource: dict) -> str:
        """POST a new resource. Returns the server-assigned ID."""
        url = self._url(resource_type)
        resp = self._session.post(url, json=resource, timeout=FHIR_TIMEOUT)
        self._raise_for_fhir_error(resp)
        resource_id = resp.json()["id"]
        logger.info("Created %s/%s", resource_type, resource_id)
        return resource_id

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def read(self, resource_type: str, resource_id: str) -> dict:
        """GET a single resource by ID."""
        url = self._url(resource_type, resource_id)
        resp = self._session.get(url, timeout=FHIR_TIMEOUT)
        self._raise_for_fhir_error(resp)
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def search(self, resource_type: str, params: dict[str, str]) -> list[dict]:
        """GET a Bundle and return list of matching resources."""
        url = self._url(resource_type)
        resp = self._session.get(url, params=params, timeout=FHIR_TIMEOUT)
        self._raise_for_fhir_error(resp)
        bundle = resp.json()
        entries = bundle.get("entry", [])
        return [e["resource"] for e in entries]

    def delete(self, resource_type: str, resource_id: str) -> None:
        """DELETE a resource."""
        url = self._url(resource_type, resource_id)
        resp = self._session.delete(url, timeout=FHIR_TIMEOUT)
        self._raise_for_fhir_error(resp)
        logger.info("Deleted %s/%s", resource_type, resource_id)

    def ping(self) -> bool:
        """Check server reachability via /metadata."""
        try:
            resp = self._session.get(
                f"{self.base_url}/metadata",
                timeout=5,
                headers={"Accept": "application/fhir+json"},
            )
            return resp.status_code == 200
        except Exception:
            return False
