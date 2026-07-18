# lu-eli-mcp

<!-- mcp-name: io.github.matematicsolutions/lu-eli-mcp -->


## Install (one command)

Published on PyPI + MCP Registry (`io.github.matematicsolutions/lu-eli-mcp`). Run without cloning:

```bash
uvx lu-eli-mcp
```

Configure your MCP client (stdio):

```json
{ "mcpServers": { "lu-eli-mcp": { "command": "uvx", "args": ["lu-eli-mcp"] } } }
```

### Windows 11 with Smart App Control

Smart App Control blocks unsigned executables, which covers `uvx.exe`, `pip.exe`
and the `lu-eli-mcp.exe` launcher that pip writes at install time. The `python.exe` and
`py.exe` from the python.org installer are signed by the Python Software
Foundation, so running the module through the interpreter works:

```bash
python -m pip install lu-eli-mcp
python -m lu_eli_mcp
```

`pip.exe` is blocked for the same reason, so install with `python -m pip`, not
`pip install`. If `python` is not on PATH, use the Windows launcher: `py -3 -m lu_eli_mcp`.

```json
{ "mcpServers": { "lu-eli-mcp": { "command": "python", "args": ["-m", "lu_eli_mcp"] } } }
```

Do not turn Smart App Control off to work around this - it cannot be re-enabled
without reinstalling Windows.

Building from source: see [Install](#install).

An MCP server for **Luxembourg legislation** via [Legilux](https://legilux.public.lu) open data
(`data.legilux.public.lu`). It fetches act metadata and full Akoma Ntoso text with verifiable
citations. Part of the **eu-legal-mcp** line of national legal connectors by
[MateMatic](https://matematic.co).

Legilux is genuinely **ELI-native**: every act is addressed by its ELI and described as jolux RDF
over a FRBR model (Work / Expression / Manifestation), with full text as Akoma Ntoso XML. Every
response carries a native `eli_uri`, a `human_readable_citation` and a resolvable `source_url`.

> **Read-only.** The server only queries Legilux and writes a local audit log. It never modifies
> official text.

## Tools

| Tool | What it does |
| --- | --- |
| `lu_get_act(eli)` | Metadata for an act by its ELI (full URI or bare `eli/...` path). Returns the native `eli_uri`, title, dates, in-force status, available languages / manifestations, and the act's `cites` / `modifies` / `repeals` links. |
| `lu_get_text(eli, language, file_format)` | Verbatim text in one `language` (default `fr`) and `file_format` (default `xml`, Akoma Ntoso). |

There is **no free-text search**: Legilux exposes no HTTP search endpoint. Discover acts by ELI
coordinates (from legilux.public.lu) or by following the `cites` / `modifies` / `repeals` ELIs that
`lu_get_act` returns. Luxembourg is multilingual, so titles and text may be French or German; the
`languages` field shows what exists for a given act.

## Configuration

Legilux is keyless. Configuration is optional:

| Variable | Meaning |
| --- | --- |
| `LU_ELI_BASE_URL` | Legilux data host (default `https://data.legilux.public.lu`). |
| `LU_ELI_CACHE_DIR` | Disk cache dir (default `~/.matematic/cache/lu-eli`). |
| `LU_ELI_AUDIT_DIR` | Audit log dir (default `~/.matematic/audit`). |

Copy `.mcp.json.example` to your MCP client config.

## Install

```bash
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"   # Windows
# or: python -m pip install -e ".[dev]"                  # POSIX
```

## Tests

```bash
pytest tests/test_instructions_drift.py tests/test_parse.py   # offline
pytest tests/test_smoke.py -v                                 # live, hits Legilux
```

## Licence

Apache-2.0. Legilux content is © the Grand Duchy of Luxembourg; this software only retrieves and
cites it.
