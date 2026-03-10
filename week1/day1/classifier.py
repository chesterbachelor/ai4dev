"""LLM-based job classification using OpenAI-compatible API."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Settings
from models import ClassifiedPerson, JobClassification, PersonRecord

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You will receive a job description. Return a short description and tag or list of tags that best categorises the job.
One person can have more than one tag (for example a person can have tag "IT" and "transport").

You can only use these tags:
- IT — person working in a computer / technology department
- transport — work that includes transportation, moving stuff around
- edukacja — person who teaches something
- medycyna — person who works in medical department, is a doctor, or works in a drug store
- praca z ludźmi — work that includes working with people (e.g. shop, restaurant, hotel)
- praca z pojazdami — work that includes driving or working with vehicles
- praca fizyczna — manual labour, or work with machines / tools
"""

RESPONSE_FORMAT = ResponseFormatJSONSchema(
    type="json_schema",
    json_schema={
        "name": "job_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short description of the job",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags that describe the job",
                },
            },
            "required": ["description", "tags"],
            "additionalProperties": False,
        },
    },
)


def _create_openai_client(settings: Settings) -> OpenAI:
    """Instantiate an OpenAI client pointed at OpenRouter."""
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _classify_single(person: PersonRecord, llm: OpenAI, model: str) -> ClassifiedPerson:
    """Send a single job description to the LLM and return the classification."""
    logger.debug("Classifying job for %s: %s", person.full_name, person.job)

    completion = llm.chat.completions.create(
        model=model,
        response_format=RESPONSE_FORMAT,
        messages=[
            ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT),
            ChatCompletionUserMessageParam(role="user", content=person.job),
        ],
    )

    classification = JobClassification.model_validate_json(
        completion.choices[0].message.content
    )

    return ClassifiedPerson(person=person, classification=classification)


def classify_jobs(
    people: list[PersonRecord],
    settings: Settings,
) -> list[ClassifiedPerson]:
    """Classify jobs for *people* concurrently and return successful results."""
    llm = _create_openai_client(settings)
    results: list[ClassifiedPerson] = []

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        future_to_person = {
            executor.submit(_classify_single, person, llm, settings.llm_model): person
            for person in people
        }
        for future in as_completed(future_to_person):
            person = future_to_person[future]
            try:
                results.append(future.result())
            except Exception:
                logger.exception("Failed to classify %s", person.full_name)

    logger.info("Successfully classified %d / %d people", len(results), len(people))
    return results

