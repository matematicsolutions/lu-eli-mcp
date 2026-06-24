# Constitution of lu-eli-mcp

Version: 0.1.0
Date: 2026-06-24
Licence: Apache-2.0

`lu-eli-mcp` is an MCP server for Luxembourg legislation via Legilux open data
(`data.legilux.public.lu`). It fetches act metadata (jolux RDF) and full text (Akoma Ntoso XML)
with verifiable, ELI-native citations.

The 4 principles below are inherited from the `eu-legal-mcp` line Constitution (Article IV).

---

## Art. 1. Public data only

Legilux is the official, public, keyless source of Luxembourg legislation, published as open data.
The server is read-only against Legilux and sends nothing beyond the requested ELI.

## Art. 2. Mandatory audit log

Every tool call MUST append one JSON line to `~/.matematic/audit/lu-eli-mcp.jsonl`
(ts / tool / input_hash SHA-256 / output_count_or_size / duration_ms / status). Inability to write =
the tool returns an error, it does not silently skip.

## Art. 3. Vendor neutrality

No tool hardcodes an LLM provider, assumes a model, or adds commercial telemetry. The server talks
only to `data.legilux.public.lu` and the local filesystem. Authentication: none; own backoff + cache.

## Art. 4. ELI citations and a human-readable citation are mandatory

Every response MUST carry three fields:
- `eli_uri`: the **native** Legilux ELI Work URI (e.g.
  `https://data.legilux.public.lu/eli/etat/leg/loi/2018/08/01/a686/jo`). Legilux is ELI-native, so
  this is parsed from the dereferenced resource, never fabricated.
- `human_readable_citation`: the `jolux:title` (Luxembourg convention, e.g. "Loi du 1er août 2018
  ...").
- `source_url`: the human-facing legilux.public.lu page for the ELI.

---

## Open points

1. **No HTTP search** - Legilux exposes no SPARQL/search endpoint over HTTP (the public SPARQL UI
   is a SPA). Discovery is by ELI coordinates and by the cites/modifies/repeals citation graph.
   A future feature could add a list/browse path if one becomes available.
2. **Multilingual** - acts may exist in French and German; `lu_get_text` takes a `language`.
3. **Binary formats** - PDF/DOCX manifestations exist but are not served as text; the connector
   focuses on Akoma Ntoso XML (and HTML).

## Constitution evolution

Changes to art. 1-4 follow SEMVER + an entry in `CHANGELOG.md` + a `pyproject.toml` bump.

First version: 2026-06-24. Author: Wieslaw Mazur / MateMatic.
