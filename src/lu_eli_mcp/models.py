"""Pydantic v2 models for Luxembourg Legilux + lu-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DATASET_NOTE = (
    "Legilux (data.legilux.public.lu) serves Luxembourg legislation as jolux RDF over a FRBR "
    "model, with full text as Akoma Ntoso XML. It is genuinely ELI-native. There is no HTTP "
    "search endpoint, so discovery is by ELI coordinates (no free-text search) - obtain ELIs "
    "from legilux.public.lu or from the cites/modifies/repeals links in lu_get_act output."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Manifestation(_Tolerant):
    """One downloadable representation of an act (language + format)."""

    language: str | None = None
    format: str | None = None
    file_url: str | None = None


class Act(_Tolerant):
    """Result of ``lu_get_act`` - metadata for a Luxembourg legal resource."""

    eli_uri: str | None = None
    eli_path: str | None = None
    title: str | None = None
    title_short: str | None = None
    type: str | None = None
    date_document: str | None = None
    publication_date: str | None = None
    date_entry_in_force: str | None = None
    in_force_status: str | None = None
    languages: list[str] = Field(default_factory=list)
    manifestations: list[Manifestation] = Field(default_factory=list)
    cites: list[str] = Field(default_factory=list)
    modifies: list[str] = Field(default_factory=list)
    repeals: list[str] = Field(default_factory=list)

    # Citation contract.
    eli_uri_native: bool = True
    human_readable_citation: str | None = None
    source_url: str | None = None
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``lu_get_text`` - the verbatim text of an act in one language/format."""

    eli_uri: str | None = None
    language: str | None = None
    format: str | None = None
    file_url: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    content: str | None = None
    byte_size: int | None = None
    dataset_note: str = DATASET_NOTE
