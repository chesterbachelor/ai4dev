"""HTTP client layer — data fetching and answer submission."""

import csv
import io
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from models import PersonRecord, VerifyPayload

logger = logging.getLogger(__name__)

# Column name mapping: CSV headers → PersonRecord fields
_CSV_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "surname": "surname",
    "gender": "gender",
    "birthDate": "birth_date",
    "birthPlace": "birth_place",
    "job": "job",
}


def _build_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a requests Session with automatic retries on transient errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_people(data_url: str) -> list[PersonRecord]:
    """Download CSV from *data_url* and parse into PersonRecord models."""
    session = _build_session()
    logger.info("Fetching people data from %s", data_url)

    response = session.get(data_url, timeout=30)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    people = [
        PersonRecord(**{_CSV_FIELD_MAP[k]: v for k, v in row.items() if k in _CSV_FIELD_MAP})
        for row in reader
    ]
    logger.info("Fetched %d person records", len(people))
    return people


def submit_answer(verify_url: str, payload: VerifyPayload) -> dict:
    """POST the verification payload and return the JSON response."""
    session = _build_session()
    logger.info("Submitting answer to %s", verify_url)

    response = session.post(verify_url, json=payload.model_dump(), timeout=30)
    response.raise_for_status()

    result = response.json()
    logger.info("Verification response: %s (HTTP %d)", result, response.status_code)
    return result

