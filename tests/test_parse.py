"""Offline parse tests - feed the saved Legilux RDF/AKN fixtures through the parser.

No network. Asserts the citation contract (native eli_uri / human_readable_citation /
source_url) and the FRBR manifestation mapping.
"""

from __future__ import annotations

from pathlib import Path

from lu_eli_mcp import citations

FIXTURES = Path(__file__).parent / "fixtures"
ELI_PATH = "eli/etat/leg/loi/2018/08/01/a686/jo"


def _rdf() -> str:
    return (FIXTURES / "act_loi_2018.rdf").read_text(encoding="utf-8")


def test_normalize_eli_variants():
    full = "https://data.legilux.public.lu/eli/etat/leg/loi/2018/08/01/a686/jo"
    web = "https://legilux.public.lu/eli/etat/leg/loi/2018/08/01/a686/jo"
    assert citations.normalize_eli(full) == ELI_PATH
    assert citations.normalize_eli(web) == ELI_PATH
    assert citations.normalize_eli(ELI_PATH) == ELI_PATH
    assert citations.normalize_eli("not an eli") is None
    assert citations.normalize_eli("") is None


def test_parse_act_contract():
    act = citations.parse_act(_rdf(), ELI_PATH)
    assert act is not None
    assert act["eli_uri"] == "https://data.legilux.public.lu/" + ELI_PATH
    assert act["type"] == "LOI"
    assert act["date_document"] == "2018-08-01"
    assert act["publication_date"] == "2018-08-16"
    assert act["in_force_status"] == "in-force"
    assert act["human_readable_citation"] and act["human_readable_citation"].startswith("Loi du")
    assert act["source_url"] == "https://legilux.public.lu/" + ELI_PATH
    assert "fr" in act["languages"]


def test_parse_act_manifestations_and_xml_lookup():
    act = citations.parse_act(_rdf(), ELI_PATH)
    assert act is not None
    formats = {(m["language"], m["format"]) for m in act["manifestations"]}
    assert ("fr", "xml") in formats
    file_url = citations.find_manifestation(act, "fr", "xml")
    assert file_url and file_url.endswith(".xml") and "filestore" in file_url
    assert citations.find_manifestation(act, "fr", "nope") is None


def test_parse_act_relations_present():
    act = citations.parse_act(_rdf(), ELI_PATH)
    assert act is not None
    # The 2018 data-protection law cites the GDPR and modifies/repeals earlier laws.
    assert any("reg_ue/2016/679" in c for c in act["cites"])
    assert act["modifies"] or act["repeals"]


def test_text_fixture_is_akoma_ntoso():
    txt = (FIXTURES / "act_loi_2018_text.xml").read_text(encoding="utf-8")
    assert "akomaNtoso" in txt


def test_eli_uri_is_native_not_fabricated():
    act = citations.parse_act(_rdf(), ELI_PATH)
    assert act is not None
    # eli_uri must be the dereferenced Legilux resource, i.e. derived from the input path.
    assert act["eli_uri"].endswith(ELI_PATH)
