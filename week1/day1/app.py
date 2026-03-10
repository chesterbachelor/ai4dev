"""People classification pipeline.

Fetches person records from a remote CSV, filters by demographics,
classifies jobs via an LLM, and submits transport-tagged workers
to a verification endpoint.
"""

import logging
import sys

from classifier import classify_jobs
from client import fetch_people, submit_answer
from config import Settings
from filters import build_transport_answer, filter_target_people

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the full classification-and-submit pipeline."""
    settings = Settings()

    # 1. Fetch raw data
    people = fetch_people(settings.data_url)

    # 2. Filter to target demographic
    candidates = filter_target_people(people, settings)

    # 3. Classify each candidate's job via LLM
    classified = classify_jobs(candidates, settings)

    # 4. Build final payload for transport workers
    payload = build_transport_answer(classified, settings)
    logger.info("Payload contains %d transport workers", len(payload.answer))
    logger.info("Payload: %s", payload)

    # 5. Submit and report
    result = submit_answer(settings.verify_url, payload)
    logger.info("Done — server responded: %s", result)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)

