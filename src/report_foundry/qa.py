"""Report-level quality gates for admissible artifacts.

Lattice: RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

from pydantic import BaseModel

from .ir import Claim, Figure, Report, TableBlock


class QualityCheck(BaseModel):
    code: str
    message: str
    severity: str = "error"
    location: str | None = None


class QualityResult(BaseModel):
    ok: bool
    checks: list[QualityCheck]


def run_quality_gates(report: Report) -> QualityResult:
    checks: list[QualityCheck] = []
    if not report.title.strip():
        checks.append(QualityCheck(code="missing_title", message="Report title is required."))

    for section_index, section in enumerate(report.sections):
        if not section.title.strip():
            checks.append(QualityCheck(code="missing_section_title", message="Section title is required.", location=f"sections[{section_index}]"))
        for block_index, block in enumerate(section.blocks):
            location = f"sections[{section_index}].blocks[{block_index}]"
            if isinstance(block, Claim) and not block.citations:
                checks.append(QualityCheck(code="unsupported_claim", message="Claim has no citations.", location=location))
            if isinstance(block, Figure):
                if not block.alt_text:
                    checks.append(QualityCheck(code="missing_alt_text", message="Figure needs alt text or explicit decorative handling.", location=location, severity="warning"))
                if not block.path:
                    checks.append(QualityCheck(code="missing_renderable_visual", message="Figure must reference a software-rendered visual asset.", location=location))
            if isinstance(block, TableBlock):
                width = len(block.headers)
                for row_index, row in enumerate(block.rows):
                    if len(row) != width:
                        checks.append(QualityCheck(code="ragged_table", message="Table row width does not match headers.", location=f"{location}.rows[{row_index}]"))
    return QualityResult(ok=not any(c.severity == "error" for c in checks), checks=checks)
