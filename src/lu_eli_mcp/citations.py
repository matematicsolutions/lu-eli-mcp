"""Luxembourg Legilux (jolux RDF) parsing + citation helpers.

Legilux exposes legislation as RDF/XML using the jolux ontology
(``http://data.legilux.public.lu/resource/ontology/jolux#``) over a FRBR model:

- the **Work** node (the ELI URI, e.g. ``.../eli/etat/leg/loi/2018/08/01/a686/jo``) carries
  the type, dates and in-force status;
- one **Expression** per language (``.../jo/fr``) carries the ``jolux:title``;
- one **Manifestation** per format (``.../jo/fr/xml``) carries ``jolux:isExemplifiedBy``
  pointing at the actual file (Akoma Ntoso XML, HTML, PDF, DOCX) in the filestore.

Citation contract (Art. 4 CONSTITUTION):
- ``eli_uri``: the **native** ELI Work URI (Legilux is genuinely ELI-native - no fabrication).
- ``human_readable_citation``: the ``jolux:title`` (Luxembourg convention, e.g.
  "Loi du 1er août 2018 portant organisation de la Commission nationale pour la protection
  des données").
- ``source_url``: the human-facing legilux.public.lu page for the ELI.

Parsed with the stdlib ElementTree - no third-party RDF dependency.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
JOLUX_NS = "http://data.legilux.public.lu/resource/ontology/jolux#"

DATA_BASE = "https://data.legilux.public.lu"
WEB_BASE = "https://legilux.public.lu"

_ABOUT = f"{{{RDF_NS}}}about"
_RESOURCE = f"{{{RDF_NS}}}resource"


def normalize_eli(value: str | None) -> str | None:
    """Reduce any Legilux ELI (full URI or bare path) to the ``eli/...`` path.

    ``https://data.legilux.public.lu/eli/etat/leg/loi/2018/08/01/a686/jo`` ->
    ``eli/etat/leg/loi/2018/08/01/a686/jo``.
    """
    if not value or not value.strip():
        return None
    v = value.strip()
    idx = v.find("eli/")
    if idx == -1:
        return None
    path = v[idx:].strip("/")
    return path or None


def _ln(tag: str) -> str:
    return tag.split("}")[-1]


def _descriptions(root: ET.Element) -> list[ET.Element]:
    return root.findall(f"{{{RDF_NS}}}Description")


def _jolux_text(node: ET.Element, name: str) -> str | None:
    el = node.find(f"{{{JOLUX_NS}}}{name}")
    if el is not None and el.text and el.text.strip():
        return el.text.strip()
    return None


def _jolux_res(node: ET.Element, name: str) -> str | None:
    el = node.find(f"{{{JOLUX_NS}}}{name}")
    if el is not None:
        return el.get(_RESOURCE)
    return None


def _jolux_res_all(node: ET.Element, name: str) -> list[str]:
    out = []
    for el in node.findall(f"{{{JOLUX_NS}}}{name}"):
        res = el.get(_RESOURCE)
        if res:
            out.append(res)
    return out


def _is_type(node: ET.Element, fragment: str) -> bool:
    return any(fragment in (t.get(_RESOURCE) or "") for t in node.findall(f"{{{RDF_NS}}}type"))


def _authority_tail(uri: str | None) -> str | None:
    if not uri:
        return None
    return uri.rstrip("/").split("/")[-1] or None


def parse_act(rdf_text: str, eli_path: str) -> dict[str, Any] | None:
    """Parse a Legilux RDF/XML dereference into the citation contract + metadata."""
    try:
        root = ET.fromstring(rdf_text)
    except ET.ParseError:
        return None

    descriptions = _descriptions(root)
    work_uri = f"{DATA_BASE}/{eli_path}"

    work = next(
        (d for d in descriptions if (d.get(_ABOUT) or "").rstrip("/") == work_uri.rstrip("/")),
        None,
    )
    if work is None:
        work = next((d for d in descriptions if _is_type(d, "#Work")), None)
    if work is None:
        return None

    # Expressions (language-specific) carry the title.
    expressions = [d for d in descriptions if _is_type(d, "#Expression")]
    title = None
    title_short = None
    languages: list[str] = []
    for expr in expressions:
        about = expr.get(_ABOUT) or ""
        lang = about.rstrip("/").split("/")[-1]
        if lang:
            languages.append(lang)
        if title is None:
            title = _jolux_text(expr, "title")
            title_short = _jolux_text(expr, "titleShort")

    # Manifestations: map (language, format) -> file URL.
    manifestations: list[dict[str, Any]] = []
    for man in descriptions:
        if not _is_type(man, "#Manifestation"):
            continue
        about = man.get(_ABOUT) or ""
        tail = about.split("/jo/")[-1] if "/jo/" in about else about.rsplit("/", 2)[-1]
        parts = tail.split("/")
        lang = parts[0] if len(parts) >= 2 else None
        fmt = _authority_tail(_jolux_res(man, "format")) or (parts[1] if len(parts) >= 2 else None)
        file_url = _jolux_res(man, "isExemplifiedBy")
        manifestations.append(
            {
                "language": lang,
                "format": (fmt or "").lower(),
                "file_url": file_url,
            }
        )

    out: dict[str, Any] = {
        "eli_uri": work_uri,
        "eli_path": eli_path,
        "title": title,
        "title_short": title_short,
        "type": _authority_tail(_jolux_res(work, "typeDocument")),
        "date_document": _jolux_text(work, "dateDocument"),
        "publication_date": _jolux_text(work, "publicationDate"),
        "date_entry_in_force": _jolux_text(work, "dateEntryInForce"),
        "in_force_status": _authority_tail(_jolux_res(work, "inForceStatus")),
        "languages": sorted(set(languages)),
        "manifestations": manifestations,
        "human_readable_citation": title or title_short,
        "source_url": f"{WEB_BASE}/{eli_path}",
        "cites": _jolux_res_all(work, "cites"),
        "modifies": _jolux_res_all(work, "modifies"),
        "repeals": _jolux_res_all(work, "repeals"),
    }
    return out


def find_manifestation(act: dict[str, Any], language: str, file_format: str) -> str | None:
    """Return the file URL for a (language, format) manifestation, or None."""
    language = language.lower()
    file_format = file_format.lower()
    for man in act.get("manifestations") or []:
        if (man.get("language") or "").lower() == language and (
            man.get("format") or ""
        ).lower() == file_format:
            return man.get("file_url")
    return None
