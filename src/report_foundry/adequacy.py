"""Research adequacy and artifact QA gates for E2E runs.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .research_intake import ResearchIntake


class AdequacyCheck(BaseModel):
    code: str
    message: str
    severity: str = "warning"


class AdequacyResult(BaseModel):
    ok: bool
    checks: list[AdequacyCheck]


def run_research_adequacy_gates(intake: ResearchIntake) -> AdequacyResult:
    """Check whether a structurally valid intake looks deep enough for a report."""
    checks: list[AdequacyCheck] = []
    if len(intake.sources) < 3:
        checks.append(AdequacyCheck(code="low_source_count", message="Fewer than three observed sources were provided."))
    reliable_sources = [source for source in intake.sources if source.reliability in {"high", "medium"}]
    if len(reliable_sources) < 2:
        checks.append(AdequacyCheck(code="low_reliable_source_count", message="Fewer than two high/medium reliability sources were provided."))
    source_types = {source.source_type.lower() for source in intake.sources}
    if len(source_types) < 2 and len(intake.sources) > 1:
        checks.append(AdequacyCheck(code="low_source_type_diversity", message="Observed sources have limited type diversity."))
    if len(intake.facts) < max(3, len(intake.report.sections) * 2):
        checks.append(AdequacyCheck(code="thin_fact_base", message="Fact count is low relative to report section count."))
    for section in intake.report.sections:
        if len(section.body.split()) < 60:
            checks.append(AdequacyCheck(code="thin_section_body", message=f"Section {section.id} has fewer than 60 words."))
    if not intake.uncertainties and not intake.research_gaps and not intake.failed_sources:
        checks.append(AdequacyCheck(code="missing_uncertainty_surface", message="No uncertainties, research gaps, or failed sources were declared."))
    if not intake.methodology.known_limitations:
        checks.append(AdequacyCheck(code="missing_methodology_limitations", message="Methodology declares no known limitations."))
    return AdequacyResult(ok=not any(check.severity == "error" for check in checks), checks=checks)


def run_artifact_qa(paths: dict[str, Path]) -> AdequacyResult:
    """Verify rendered artifacts are present and have reader-QA metadata."""
    checks: list[AdequacyCheck] = []
    for key in ("pdf", "html", "package_manifest"):
        path = paths.get(key)
        if path is None or not path.exists():
            checks.append(AdequacyCheck(code=f"missing_{key}", message=f"Missing required artifact: {key}.", severity="error"))
    pdf = paths.get("pdf")
    if pdf and pdf.exists() and not pdf.read_bytes().startswith(b"%PDF"):
        checks.append(AdequacyCheck(code="invalid_pdf_header", message="PDF does not start with %PDF.", severity="error"))
    metrics_path = paths.get("layout_metrics")
    if metrics_path is None or not metrics_path.exists():
        checks.append(AdequacyCheck(code="missing_layout_metrics", message="No PDF layout metrics were written.", severity="error"))
    else:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if int(metrics.get("page_count", 0)) < 1:
            checks.append(AdequacyCheck(code="empty_pdf", message="PDF has no pages.", severity="error"))
        if float(metrics.get("average_words_per_page", 0)) < 80:
            checks.append(AdequacyCheck(code="low_pdf_density", message="PDF average words/page is below reader-quality floor."))
    previews = paths.get("page_previews")
    if previews is None or not previews.exists() or not any(previews.glob("*.png")):
        checks.append(AdequacyCheck(code="missing_page_previews", message="No page preview PNGs were written for visual QA.", severity="error"))
    return AdequacyResult(ok=not any(check.severity == "error" for check in checks), checks=checks)
