"""Domain models for the people classification pipeline."""

from enum import StrEnum

from pydantic import BaseModel


class JobTag(StrEnum):
    """Allowed job classification tags."""

    IT = "IT"
    TRANSPORT = "transport"
    EDUKACJA = "edukacja"
    MEDYCYNA = "medycyna"
    PRACA_Z_LUDZMI = "praca z ludźmi"
    PRACA_Z_POJAZDAMI = "praca z pojazdami"
    PRACA_FIZYCZNA = "praca fizyczna"


class PersonRecord(BaseModel):
    """A single row from the upstream CSV data source."""

    name: str
    surname: str
    gender: str
    birth_date: str
    birth_place: str
    job: str

    @property
    def birth_year(self) -> int:
        return int(self.birth_date.split("-")[0])

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"


class JobClassification(BaseModel):
    """Structured response returned by the LLM."""

    description: str
    tags: list[str]


class ClassifiedPerson(BaseModel):
    """A person record enriched with LLM classification."""

    person: PersonRecord
    classification: JobClassification


class TransportWorker(BaseModel):
    """Final answer item for a transport-tagged worker."""

    name: str
    surname: str
    gender: str
    born: str
    city: str
    tags: list[str]


class VerifyPayload(BaseModel):
    """Payload sent to the verification endpoint."""

    apikey: str
    task: str = "people"
    answer: list[TransportWorker]

