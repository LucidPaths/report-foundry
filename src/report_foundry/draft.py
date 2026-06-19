"""Markdown draft ingestion for authored reports.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from .evidence import DraftExhibit, EvidenceClaim, EvidenceFact, EvidencePack, ReportNarrativeSection, SourceObservation

_DIRECTIVE = re.compile(r"^:::(?P<kind>source|claim|exhibit)\s*$", re.MULTILINE)
_HEADING = re.compile(r"^(#{1,2})\s+(.+?)\s*$", re.MULTILINE)


def parse_markdown_draft(markdown: str, *, author: str = "Research Author", observed_at: str | None = None) -> EvidencePack:
    """Parse an authored Markdown report into the Foundry evidence spine.

    The report author owns the report prose and visual intent. This parser only normalizes
    sources, claims, sections, and exhibit directives so existing compiler and
    renderer adapters can do their one job.
    """

    observed_at = observed_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    directives, prose = _extract_directives(markdown)
    title = _extract_title(prose)
    sections = _extract_sections(prose)
    sources = _source_observations(directives.get("source", []), observed_at)
    source_ids = {source.source_id for source in sources}
    facts, claims = _facts_and_claims(directives.get("claim", []), sources_by_id={source.source_id: source for source in sources})
    facts_by_source = _facts_by_source(facts)
    exhibits = _exhibits(directives.get("exhibit", []), facts_by_source=facts_by_source, source_ids=source_ids)
    return EvidencePack(
        title=title,
        author=author,
        scope={"input": "authored_markdown_draft", "audience": "report readers"},
        sources=sources,
        facts=facts,
        claims=claims,
        report_sections=sections,
        exhibits=exhibits,
        tags=["authored-draft", "compiled-draft"],
    )


def parse_markdown_draft_file(path: Path, *, author: str = "Research Author") -> EvidencePack:
    return parse_markdown_draft(path.read_text(encoding="utf-8"), author=author)


def _extract_directives(markdown: str) -> tuple[dict[str, list[dict[str, str]]], str]:
    directives: dict[str, list[dict[str, str]]] = {"source": [], "claim": [], "exhibit": []}
    output: list[str] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^:::(source|claim|exhibit)\s*$", lines[index])
        if not match:
            output.append(lines[index])
            index += 1
            continue
        kind = match.group(1)
        index += 1
        block: list[str] = []
        while index < len(lines) and not re.match(r"^::: *$", lines[index]):
            block.append(lines[index])
            index += 1
        if index < len(lines):
            index += 1
        directives[kind].append(_parse_directive_body(block))
    return directives, "\n".join(output)


def _parse_directive_body(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.rstrip() == "payload:":
            values["payload"] = "\n".join(lines[index + 1 :]).strip()
            break
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
        index += 1
    return values


def _extract_title(prose: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", prose, flags=re.MULTILINE)
    if not match:
        raise ValueError("Markdown draft requires a level-1 title")
    return match.group(1).strip()


def _extract_sections(prose: str) -> list[ReportNarrativeSection]:
    title_match = re.search(r"^#\s+(.+?)\s*$", prose, flags=re.MULTILINE)
    if not title_match:
        raise ValueError("Markdown draft requires a level-1 title")
    body = prose[title_match.end() :].strip()
    parts = re.split(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)
    sections: list[ReportNarrativeSection] = []
    if parts[0].strip():
        sections.append(_section("executive_brief", "Executive brief", parts[0]))
    for offset in range(1, len(parts), 2):
        heading = parts[offset].strip()
        content = parts[offset + 1] if offset + 1 < len(parts) else ""
        if content.strip():
            sections.append(_section(_slug(heading), heading, content))
    if not sections:
        raise ValueError("Markdown draft requires report prose outside directives")
    return sections


def _section(section_id: str, title: str, content: str) -> ReportNarrativeSection:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content.strip()) if paragraph.strip()]
    return ReportNarrativeSection(section_id=section_id, title=title, paragraphs=paragraphs)


def _source_observations(blocks: list[dict[str, str]], observed_at: str) -> list[SourceObservation]:
    _SOURCE_QUOTES.clear()
    sources: list[SourceObservation] = []
    for block in blocks:
        source_id = _required(block, "id", "source")
        title = _required(block, "title", source_id)
        quote = _required(block, "quote", source_id)
        _SOURCE_QUOTES[source_id] = quote
        url = block.get("url")
        payload = "\n".join([source_id, title, url or "", quote]).encode("utf-8")
        sources.append(
            SourceObservation(
                source_id=source_id,
                title=title,
                url=url,
                observed_at=observed_at,
                content_sha256=hashlib.sha256(payload).hexdigest(),
                extractor="authored-draft-directive",
                locator="markdown :::source",
            )
        )
    return sources


def _facts_and_claims(blocks: list[dict[str, str]], *, sources_by_id: dict[str, SourceObservation]) -> tuple[list[EvidenceFact], list[EvidenceClaim]]:
    facts: list[EvidenceFact] = []
    claims: list[EvidenceClaim] = []
    for index, block in enumerate(blocks, 1):
        claim_id = block.get("id") or f"claim_{index:03d}"
        text = _required(block, "text", claim_id)
        source_id = _required(block, "source", claim_id)
        if source_id not in sources_by_id:
            raise ValueError(f"Claim {claim_id} references unknown source {source_id}")
        fact_id = f"fact_{_slug(claim_id)}"
        source = sources_by_id[source_id]
        facts.append(
            EvidenceFact(
                fact_id=fact_id,
                subject=claim_id,
                predicate="supports_claim",
                value=text,
                source_id=source_id,
                quote=source.locator if False else _source_quote_placeholder(source),
                locator="markdown :::claim",
            )
        )
        claims.append(EvidenceClaim(text=text, fact_ids=[fact_id], confidence=block.get("confidence", "unknown")))
    return facts, claims


def _source_quote_placeholder(source: SourceObservation) -> str:
    # SourceObservation stores payload hash/metadata, not the raw quote. The draft
    # parser duplicates the source quote into the fact via _SOURCE_QUOTES below.
    return _SOURCE_QUOTES.get(source.source_id, source.title)


_SOURCE_QUOTES: dict[str, str] = {}


def _facts_by_source(facts: list[EvidenceFact]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for fact in facts:
        grouped.setdefault(fact.source_id, []).append(fact.fact_id)
    return grouped


def _exhibits(blocks: list[dict[str, str]], *, facts_by_source: dict[str, list[str]], source_ids: set[str]) -> list[DraftExhibit]:
    exhibits: list[DraftExhibit] = []
    for block in blocks:
        source_id = _required(block, "source", block.get("id", "exhibit"))
        if source_id not in source_ids:
            raise ValueError(f"Exhibit {block.get('id', '<unknown>')} references unknown source {source_id}")
        fact_ids = facts_by_source.get(source_id, [])
        exhibits.append(
            DraftExhibit(
                visual_id=_required(block, "id", "exhibit"),
                visual_type=block.get("type", "diagram"),
                title=block.get("title"),
                purpose=_required(block, "purpose", block.get("id", "exhibit")),
                preferred_tool=block.get("renderer", "mermaid"),
                provenance_fact_ids=fact_ids,
                plain_text_payload=_required(block, "payload", block.get("id", "exhibit")),
            )
        )
    return exhibits


def _required(block: dict[str, str], key: str, context: str) -> str:
    value = block.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing {key} in draft directive {context}")
    return value


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "section"
