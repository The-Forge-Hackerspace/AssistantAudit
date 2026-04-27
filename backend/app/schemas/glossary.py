"""Schemas pour le glossaire dynamique du rapport (TOS-25 section 8)."""

from pydantic import BaseModel, Field


class GlossaryEntry(BaseModel):
    """Une entree du glossaire — terme + definition."""

    term: str
    definition: str
    aliases: list[str] = Field(default_factory=list)


class Glossary(BaseModel):
    """Glossaire dynamique : termes detectes dans les controles de l'audit."""

    audit_id: int
    entries: list[GlossaryEntry] = Field(default_factory=list)
    total: int = 0
