"""Filtering and result-building utilities."""

import logging

from config import Settings
from models import (
    ClassifiedPerson,
    JobTag,
    PersonRecord,
    TransportWorker,
    VerifyPayload,
)

logger = logging.getLogger(__name__)


def filter_target_people(
    people: list[PersonRecord],
    settings: Settings,
) -> list[PersonRecord]:
    """Return people matching the configured gender, city, and age range."""
    min_birth_year = settings.current_year - settings.max_age
    max_birth_year = settings.current_year - settings.min_age

    filtered = [
        p
        for p in people
        if p.gender == settings.target_gender
        and p.birth_place == settings.target_city
        and min_birth_year <= p.birth_year <= max_birth_year
    ]

    logger.info(
        "Filtered %d → %d people (gender=%s, city=%s, age %d–%d)",
        len(people),
        len(filtered),
        settings.target_gender,
        settings.target_city,
        settings.min_age,
        settings.max_age,
    )
    return filtered


def build_transport_answer(
    classified: list[ClassifiedPerson],
    settings: Settings,
) -> VerifyPayload:
    """Extract transport-tagged workers and wrap them in a VerifyPayload."""
    transport_workers = [
        TransportWorker(
            name=cp.person.name,
            surname=cp.person.surname,
            gender=cp.person.gender,
            born=str(cp.person.birth_year),
            city=cp.person.birth_place,
            tags=cp.classification.tags,
        )
        for cp in classified
        if JobTag.TRANSPORT in cp.classification.tags
    ]

    logger.info(
        "Found %d transport workers out of %d classified",
        len(transport_workers),
        len(classified),
    )

    return VerifyPayload(
        apikey=settings.project_api_key,
        answer=transport_workers,
    )

