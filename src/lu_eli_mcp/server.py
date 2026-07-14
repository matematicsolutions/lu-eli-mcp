"""FastMCP entry point - Luxembourg Legilux legislation tools.

Run:

    python -m lu_eli_mcp.server

Configuration via env:

- ``LU_ELI_BASE_URL`` (default ``https://data.legilux.public.lu``)
- ``LU_ELI_CACHE_DIR`` (default ``~/.matematic/cache/lu-eli``)
- ``LU_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import citations
from .audit import AuditLogger, hash_input, timer
from .citations import normalize_eli, parse_act
from . import runtime
from .client import DEFAULT_BASE_URL, LegiluxClient
from .models import Act, LawText

INSTRUCTIONS = """\
This MCP server exposes Luxembourg legislation via Legilux open data (data.legilux.public.lu). Legilux is genuinely ELI-native: every act is addressed by its ELI and described as jolux RDF over a FRBR model, with full text as Akoma Ntoso XML. Every response carries the citation contract: a native `eli_uri`, a `human_readable_citation` (Luxembourg convention) and a `source_url`.

## Call order

1. `lu_get_act` - metadata for an act by its `eli` (a full Legilux ELI URI or the bare `eli/...` path, e.g. `eli/etat/leg/loi/2018/08/01/a686/jo`). Returns the native `eli_uri`, title, dates, in-force status, available `languages` / `manifestations`, and the act's `cites` / `modifies` / `repeals` links.
2. `lu_get_text` - the verbatim text of an act in one `language` (default `fr`) and `file_format` (default `xml`, i.e. Akoma Ntoso). Returns `content` plus the citation contract.

## Hard constraints

- **No free-text search** - Legilux exposes no HTTP search endpoint. Discover acts by ELI coordinates (from legilux.public.lu) or by following the `cites` / `modifies` / `repeals` ELIs returned by `lu_get_act`. Relay the `dataset_note`.
- **ELI is native** - the `eli_uri` is the genuine Legilux ELI Work URI; do not invent or alter it.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **No modification of official text** - text is returned verbatim (Akoma Ntoso) from Legilux.
- **Luxembourg is multilingual** - titles and text may be French, German or others; use `languages` to see what exists.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/lu-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - a parameter is missing or not a recognizable Legilux ELI.
- `not_found` - no act, language or format exists for that ELI.
- `upstream_error` - a Legilux error (HTTP, timeout, malformed RDF). Retry once before surfacing.

## Response style

- Cite acts as `human_readable_citation` with the ELI: "Loi du 1er août 2018 ..., https://legilux.public.lu/eli/etat/leg/loi/2018/08/01/a686/jo".
- NEVER invent an ELI, a title or a date - take each from the tool output.
"""


class ToolError(Exception):
    """Structured error for lu-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="lu-eli-mcp", instructions=INSTRUCTIONS)


def _base_url() -> str:
    return os.environ.get("LU_ELI_BASE_URL", runtime.base_url("eli", DEFAULT_BASE_URL)).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return ToolError("not_found", "No resource found in Legilux for that ELI.")
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"Legilux error: {type(exc).__name__}: {exc}")
    return exc


def _require_eli(eli: str) -> str:
    path = normalize_eli(eli)
    if not path:
        raise ToolError(
            "invalid_arg",
            f"eli={eli!r} is not a recognizable Legilux ELI (expected an 'eli/...' path or URI).",
        )
    return path


# ---------------------------------------------------------------------------
# lu_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def lu_get_act(eli: str) -> Act:
    """Fetch metadata for a Luxembourg act by its ELI.

    Args:
        eli: a Legilux ELI - full URI or bare path (e.g. ``eli/etat/leg/loi/2018/08/01/a686/jo``).

    Returns:
        ``Act`` with the native ``eli_uri``, ``human_readable_citation``, ``source_url``,
        dates, in-force status and the available languages / manifestations.
    """
    audit = _audit()
    eli_path = _require_eli(eli)
    input_hash = hash_input({"eli": eli_path})

    with timer() as t:
        try:
            async with LegiluxClient(base_url=_base_url()) as client:
                rdf = await client.get_rdf(eli_path)
        except Exception as exc:
            audit.log(tool="lu_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms or 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    parsed = parse_act(rdf, eli_path)
    if parsed is None:
        raise ToolError("not_found", f"No act metadata found for {eli_path}.")
    act = Act.model_validate(parsed)
    audit.log(tool="lu_get_act", input_hash=input_hash, output_count_or_size=len(act.manifestations),
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# lu_get_text
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def lu_get_text(eli: str, language: str = "fr", file_format: str = "xml") -> LawText:
    """Fetch the verbatim text of a Luxembourg act in one language and format.

    Args:
        eli: a Legilux ELI - full URI or bare path.
        language: e.g. ``fr`` (default) or ``de``.
        file_format: ``xml`` (Akoma Ntoso, default) or ``html``.

    Returns:
        ``LawText`` with ``content`` and the citation contract.
    """
    audit = _audit()
    eli_path = _require_eli(eli)
    language = (language or "fr").strip().lower()
    file_format = (file_format or "xml").strip().lower()
    input_hash = hash_input({"eli": eli_path, "language": language, "file_format": file_format})

    with timer() as t:
        try:
            async with LegiluxClient(base_url=_base_url()) as client:
                rdf = await client.get_rdf(eli_path)
                parsed = parse_act(rdf, eli_path)
                if parsed is None:
                    raise ToolError("not_found", f"No act metadata found for {eli_path}.")
                file_url = citations.find_manifestation(parsed, language, file_format)
                if not file_url:
                    avail = sorted(
                        {
                            f"{m.get('language')}/{m.get('format')}"
                            for m in parsed.get("manifestations") or []
                        }
                    )
                    raise ToolError(
                        "not_found",
                        f"No {language}/{file_format} manifestation for {eli_path}. Available: {avail}.",
                    )
                content = await client.get_file(file_url)
        except ToolError:
            audit.log(tool="lu_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms or 0, status="error", error="tool_error")
            raise
        except Exception as exc:
            audit.log(tool="lu_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms or 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    result = LawText(
        eli_uri=parsed.get("eli_uri"),
        language=language,
        format=file_format,
        file_url=file_url,
        human_readable_citation=parsed.get("human_readable_citation"),
        source_url=parsed.get("source_url"),
        content=content,
        byte_size=len(content.encode("utf-8")),
    )
    audit.log(tool="lu_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
