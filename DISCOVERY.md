# Discovery - lu-eli-mcp (Luxembourg Legilux)

Date: 2026-06-24. Decision: **BUILD** (clean keyless ELI-native source, reachable this session).

## Context

In the prior eu-legal-mcp sweeps, Luxembourg was logged as "unreachable from this network
(timeout)". A fresh recon of the unexplored EU-27 (BE/BG/HR/GR/HU/LT/LV/RO/SI + LU) found those
others are HTML/SPA/blocked, but **Legilux is now reachable and machine-readable** via RDF content
negotiation.

## Source (probed live, not trusted from docs)

- **Host:** `https://data.legilux.public.lu`. Keyless.
- **ELI-native dereference:** `GET https://data.legilux.public.lu/{eli-path}` with
  `Accept: application/rdf+xml` returns jolux RDF/XML for the resource. (The `legilux.public.lu`
  front and the `data.legilux/sparql` console are SPA shells; `Accept: application/ld+json` gives
  415, but `application/rdf+xml` works.)
- **No HTTP SPARQL:** `POST /sparql` returns 405, `GET /sparql?query=` returns the SPA. So there is
  no free-text search - the connector is by-coordinate, like ie-eli-mcp.
- **Full text:** each act has manifestations (`/{lang}/xml|html|pdfa|docx`). The manifestation node
  in the RDF carries `jolux:isExemplifiedBy` pointing at the actual file in the filestore
  (`https://data.legilux.public.lu/filestore/.../eli-...-fr-xml.xml`). The `xml` manifestation is
  **Akoma Ntoso 3.0** (84 KB for the test act). The `/{lang}/xml` resource URL itself returns 500;
  the filestore URL from the RDF returns 200 - so we follow the RDF link rather than construct it.

## jolux RDF shape (FRBR)

- **Work** node (the ELI URI, ends `/jo`): `typeDocument` (LOI/...), `dateDocument`,
  `publicationDate`, `dateEntryInForce`, `inForceStatus`, `isRealizedBy` (expressions),
  `isMemberOf`, `isPartOf`, plus a citation graph: `cites` / `modifies` / `repeals` / `draft`.
- **Expression** node (`/jo/fr`): `jolux:title`, `jolux:titleShort`, language.
- **Manifestation** node (`/jo/fr/xml`): `jolux:format` + `jolux:isExemplifiedBy` (file URL).

## Citation contract mapping

| Field | Source |
| --- | --- |
| `eli_uri` | the native Work URI (`data.legilux.public.lu/{eli}`) |
| `human_readable_citation` | `jolux:title` from the French expression ("Loi du 1er août 2018 ...") |
| `source_url` | `https://legilux.public.lu/{eli}` (human portal) |

## Build

`audit.py` + `cache.py` reused verbatim (env `LU_ELI_*`, log `lu-eli-mcp.jsonl`). New per LU:
`client.py` (keyless GET: RDF dereference + filestore file fetch), `citations.py` (jolux RDF parse
via stdlib ElementTree + ELI normalization), `models.py`, `server.py` (2 tools: `lu_get_act`,
`lu_get_text`; `ToolError` {invalid_arg / not_found / upstream_error}). Tests: offline drift +
offline fixture parse + live smoke. The factory holds: infrastructure reused, only the source
adapter is new.
