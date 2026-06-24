"""Smoke tests - require internet, hit the live Legilux open data.

Run manually:

    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import pytest

from lu_eli_mcp.server import lu_get_act, lu_get_text

# Loi du 1er août 2018 (data-protection organisation law).
ELI = "eli/etat/leg/loi/2018/08/01/a686/jo"


@pytest.mark.asyncio
async def test_smoke_get_act() -> None:
    act = await lu_get_act(ELI)
    assert act.eli_uri and act.eli_uri.endswith(ELI)
    assert act.type == "LOI"
    assert act.human_readable_citation and act.human_readable_citation.startswith("Loi du")
    assert act.source_url and act.source_url.startswith("https://legilux.public.lu/")
    assert "fr" in act.languages
    assert any(m.format == "xml" for m in act.manifestations)


@pytest.mark.asyncio
async def test_smoke_get_act_accepts_full_uri() -> None:
    act = await lu_get_act("https://legilux.public.lu/" + ELI)
    assert act.type == "LOI"


@pytest.mark.asyncio
async def test_smoke_get_text_akoma_ntoso() -> None:
    text = await lu_get_text(ELI, language="fr", file_format="xml")
    assert text.content and "akomaNtoso" in text.content
    assert text.byte_size and text.byte_size > 0
    assert text.eli_uri and text.eli_uri.endswith(ELI)
    assert text.file_url and "filestore" in text.file_url
