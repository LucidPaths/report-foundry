"""Fixture adapter for local marked sources.

This is not the product AI/search path. It exercises the foundry
source-observation -> fact -> claim -> gate contract without external calls.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from .evidence import EvidenceClaim, EvidenceFact, EvidencePack, SourceObservation
from .factory import FactoryGateResult, PageMetrics, ReportRunManifest, SourcePlan, evaluate_factory_gates


class ResearchResult(BaseModel):
    manifest: ReportRunManifest
    source_plan: SourcePlan
    evidence: EvidencePack
    gate_result: FactoryGateResult


def build_research_evidence(*, run_dir: Path, source_dir: Path) -> ResearchResult:
    manifest = ReportRunManifest.model_validate_json((run_dir / "manifest.json").read_text(encoding="utf-8"))
    source_plan = SourcePlan.model_validate_json((run_dir / "source_plan.json").read_text(encoding="utf-8"))
    source_documents = _read_source_documents(source_dir)

    sources: list[SourceObservation] = []
    facts: list[EvidenceFact] = []
    claims: list[EvidenceClaim] = []
    for document in source_documents:
        source = _source_observation(document.path, document.text)
        sources.append(source)
        for item in source_plan.items:
            quote = _extract_dimension_quote(document.text, item.dimension)
            if quote is None:
                continue
            fact_id = f"fact:{item.dimension}:{len(facts) + 1}"
            facts.append(
                EvidenceFact(
                    fact_id=fact_id,
                    subject=manifest.topic,
                    predicate=f"dimension:{item.dimension}",
                    value="covered",
                    source_id=source.source_id,
                    quote=quote,
                    locator=f"DIMENSION: {item.dimension}",
                )
            )
            claims.append(
                EvidenceClaim(
                    text=_claim_from_dimension(manifest.topic, item.dimension, quote),
                    fact_ids=[fact_id],
                    confidence="medium",
                )
            )

    evidence = EvidencePack(
        title=manifest.topic,
        subtitle="Local marked-source research evidence",
        scope={
            "research_mode": "local_marked_sources",
            "source_dir": str(source_dir),
            "required_dimensions": [item.dimension for item in source_plan.items],
        },
        sources=sources,
        facts=facts,
        claims=claims,
        tags=["factory-research", manifest.integration_mode],
    )
    gate_result = evaluate_factory_gates(
        manifest,
        evidence,
        pages=[PageMetrics(page_number=1, fill_ratio=0.8, has_source_appendix=True)],
    )
    return ResearchResult(manifest=manifest, source_plan=source_plan, evidence=evidence, gate_result=gate_result)


def write_research_artifacts(*, run_dir: Path, source_dir: Path) -> ResearchResult:
    result = build_research_evidence(run_dir=run_dir, source_dir=source_dir)
    (run_dir / "evidence_pack.json").write_text(result.evidence.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "research_gate_result.json").write_text(result.gate_result.model_dump_json(indent=2), encoding="utf-8")
    return result


class _SourceDocument(BaseModel):
    path: Path
    text: str


def _read_source_documents(source_dir: Path) -> list[_SourceDocument]:
    paths = sorted([*source_dir.glob("*.md"), *source_dir.glob("*.txt")])
    return [_SourceDocument(path=path, text=path.read_text(encoding="utf-8")) for path in paths]


def _source_observation(path: Path, text: str) -> SourceObservation:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    observed_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return SourceObservation(
        source_id=f"local:{path.name}",
        title=path.stem.replace("_", " ").replace("-", " "),
        url=path.resolve().as_uri(),
        observed_at=observed_at,
        content_sha256=digest,
        extractor="local_marked_source_v1",
        locator=str(path),
    )


def _extract_dimension_quote(text: str, dimension: str) -> str | None:
    lines = text.splitlines()
    marker = f"DIMENSION: {dimension}"
    for index, line in enumerate(lines):
        if line.strip() != marker:
            continue
        quote_lines: list[str] = []
        for following in lines[index + 1 :]:
            stripped = following.strip()
            if stripped.startswith("DIMENSION: "):
                break
            if stripped:
                quote_lines.append(stripped)
        quote = " ".join(quote_lines).strip()
        return quote or marker
    return None


def _claim_from_dimension(topic: str, dimension: str, quote: str) -> str:
    cleaned_quote = quote.strip().rstrip(".")
    return f"{topic} depends on {dimension.replace('_', ' ')} because the marked source states: {cleaned_quote}; evidence remains source-bound."
