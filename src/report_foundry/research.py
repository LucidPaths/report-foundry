"""Fixture adapter for local marked sources.

This is not the product source-acquisition path. It exercises the foundry
source-observation -> fact -> claim -> gate contract without external calls.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .evidence import EvidenceClaim, EvidenceFact, EvidencePack, SourceObservation
from .factory import FactoryGateResult, PageMetrics, ReportRunManifest, RunMode, SourcePlan, evaluate_factory_gates


class ResearchSourceCandidate(BaseModel):
    source_id: str
    path: str
    decision: Literal["selected", "rejected"]
    reason: str


class ResearchExtractionStep(BaseModel):
    source_id: str
    dimension: str
    fact_id: str
    extractor: str
    quote_locator: str


class ResearchEvidenceGap(BaseModel):
    dimension: str
    reason: str
    route_back_department: str = "research"


class ResearchRunLog(BaseModel):
    artifact_role: str = "research_run_log: source-selection, extraction, and gap audit trail"
    run_dir: str
    source_dir: str
    source_plan_dimensions: list[str]
    run_mode: RunMode = RunMode.FIXTURE
    candidates: list[ResearchSourceCandidate] = Field(default_factory=list)
    extraction_steps: list[ResearchExtractionStep] = Field(default_factory=list)
    evidence_gaps: list[ResearchEvidenceGap] = Field(default_factory=list)


class ResearchResult(BaseModel):
    manifest: ReportRunManifest
    source_plan: SourcePlan
    evidence: EvidencePack
    gate_result: FactoryGateResult
    run_log: ResearchRunLog


def build_research_evidence(*, run_dir: Path, source_dir: Path, allow_fixture_sources: bool = False) -> ResearchResult:
    manifest = ReportRunManifest.model_validate_json((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.run_mode == RunMode.PRODUCT and not allow_fixture_sources:
        raise ValueError("product mode requires a connector; local fixture sources require --allow-fixture-sources")
    source_plan = SourcePlan.model_validate_json((run_dir / "source_plan.json").read_text(encoding="utf-8"))
    source_documents = _read_source_documents(source_dir)

    sources: list[SourceObservation] = []
    facts: list[EvidenceFact] = []
    claims: list[EvidenceClaim] = []
    candidates: list[ResearchSourceCandidate] = []
    extraction_steps: list[ResearchExtractionStep] = []
    covered_dimensions: set[str] = set()
    for document in source_documents:
        source = _source_observation(document.path, document.text)
        candidates.append(
            ResearchSourceCandidate(
                source_id=source.source_id,
                path=str(document.path),
                decision="selected",
                reason="local marked source file matched fixture adapter extension",
            )
        )
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
            covered_dimensions.add(item.dimension)
            extraction_steps.append(
                ResearchExtractionStep(
                    source_id=source.source_id,
                    dimension=item.dimension,
                    fact_id=fact_id,
                    extractor=source.extractor,
                    quote_locator=f"DIMENSION: {item.dimension}",
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
            "run_mode": manifest.run_mode.value,
            "artifact_status": _artifact_status(manifest.run_mode),
            "fixture_source_override": bool(allow_fixture_sources),
            "source_dir": str(source_dir),
            "required_dimensions": [item.dimension for item in source_plan.items],
        },
        sources=sources,
        facts=facts,
        claims=claims,
        tags=["factory-research", manifest.integration_mode],
    )
    evidence_gaps = [
        ResearchEvidenceGap(
            dimension=item.dimension,
            reason="No selected marked source contained the required DIMENSION marker.",
        )
        for item in source_plan.items
        if item.dimension not in covered_dimensions
    ]
    run_log = ResearchRunLog(
        run_dir=str(run_dir),
        source_dir=str(source_dir),
        source_plan_dimensions=[item.dimension for item in source_plan.items],
        run_mode=manifest.run_mode,
        candidates=candidates,
        extraction_steps=extraction_steps,
        evidence_gaps=evidence_gaps,
    )
    gate_result = evaluate_factory_gates(
        manifest,
        evidence,
        pages=[PageMetrics(page_number=1, fill_ratio=0.8, has_source_appendix=True)],
    )
    return ResearchResult(manifest=manifest, source_plan=source_plan, evidence=evidence, gate_result=gate_result, run_log=run_log)


def write_research_artifacts(*, run_dir: Path, source_dir: Path, allow_fixture_sources: bool = False) -> ResearchResult:
    result = build_research_evidence(run_dir=run_dir, source_dir=source_dir, allow_fixture_sources=allow_fixture_sources)
    (run_dir / "evidence_pack.json").write_text(result.evidence.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "research_gate_result.json").write_text(result.gate_result.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "research_run_log.json").write_text(result.run_log.model_dump_json(indent=2), encoding="utf-8")
    return result



def _artifact_status(run_mode: RunMode) -> str:
    if run_mode == RunMode.PRODUCT:
        return "product"
    if run_mode == RunMode.EXPERIMENT:
        return "experiment"
    return "fixture"

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
        source_tier="primary",
        publisher="local fixture source",
        citation_metadata={"format": path.suffix.lstrip("."), "path": str(path)},
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
