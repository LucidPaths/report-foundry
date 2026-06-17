from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .evidence import EvidencePack, validate_evidence_pack


class Department(str, Enum):
    EDITORIAL = "editorial"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VISUALS = "visuals"
    LAYOUT = "layout"
    QA = "qa"


Severity = Literal["error", "warning"]


class RubricDimension(BaseModel):
    name: str
    description: str
    required: bool = True
    department: Department = Department.RESEARCH


class ReportRubric(BaseModel):
    topic: str
    audience: str
    report_promise: str
    required_dimensions: list[RubricDimension]
    required_source_tiers: dict[str, int] = Field(default_factory=dict)
    required_visuals: set[str] = Field(default_factory=set)
    min_hard_claims: int = 3
    final_score_minimum: int = 85
    max_pages: int = 8
    min_page_fill_ratio: float = 0.35
    require_source_appendix: bool = True


class ReportRunManifest(BaseModel):
    topic: str
    rubric: ReportRubric
    integration_mode: Literal["cli", "mcp", "server", "library"] = "cli"
    connected_sources: list[str] = Field(default_factory=list)


class PageMetrics(BaseModel):
    page_number: int
    fill_ratio: float
    has_source_appendix: bool = False
    overlap_count: int = 0
    clipped_text_count: int = 0


class FactoryGateCheck(BaseModel):
    code: str
    message: str
    department: Department
    severity: Severity = "error"


class FactoryGateResult(BaseModel):
    ok: bool
    score: int
    checks: list[FactoryGateCheck] = Field(default_factory=list)
    route_back_department: Department | None = None


SPACE_X_DIMENSIONS = [
    RubricDimension(name="valuation_and_ipo_mechanics", description="Valuation, share-sale mechanics, listing constraints, and liquidity pressure."),
    RubricDimension(name="starlink_economics", description="Starlink revenue, subscriber economics, satellite capex, and broadband market position."),
    RubricDimension(name="government_and_defense_revenue", description="NASA, defense, launch contracts, government funding, and strategic dependency."),
    RubricDimension(name="launch_cadence_and_payload_proof", description="Launch cadence, payload delivery record, reliability, and operational proof."),
    RubricDimension(name="listing_and_regulatory_mechanics", description="Exchange/listing rule changes, securities-law constraints, and timing dependencies."),
    RubricDimension(name="bull_bear_market_structure", description="Hype case, skeptic case, comparable multiples, and risk adjusted implication."),
]

EUROPEAN_BANKING_DIMENSIONS = [
    RubricDimension(name="covid_monetary_expansion", description="COVID-era money creation, fiscal backstops, and balance-sheet residue."),
    RubricDimension(name="sovereign_debt_and_war_treasuries", description="Debt loads, Ukraine-war financing, defense bonds, and treasury-market stress."),
    RubricDimension(name="regulatory_law_changes", description="Banking, capital, resolution, sanctions, and deposit-regime legal changes."),
    RubricDimension(name="gold_reserves_and_fx_trust", description="Gold reserve shifts, reserve-currency trust, and central-bank balance-sheet signaling."),
    RubricDimension(name="credit_and_real_estate_exposure", description="CRE, loan losses, deposit flight, and bank profitability pressure."),
    RubricDimension(name="ecb_policy_and_fragmentation", description="ECB policy, spreads, fragmentation risk, and country-level divergence."),
]

GENERIC_DIMENSIONS = [
    RubricDimension(name="mechanism", description="What changed, through which mechanism, and why it matters."),
    RubricDimension(name="numbers", description="Quantitative claims, baselines, and trend direction."),
    RubricDimension(name="stakeholders", description="Actors, incentives, winners, losers, and dependencies."),
    RubricDimension(name="bull_bear_cases", description="Strongest supporting and skeptical interpretations."),
    RubricDimension(name="implications", description="Actionable implications for the named audience."),
]


def build_case_rubric(topic: str, *, audience: str) -> ReportRubric:
    topic_key = topic.lower()
    if "spacex" in topic_key and "ipo" in topic_key:
        return ReportRubric(
            topic=topic,
            audience=audience,
            report_promise="Lightweight analyst-grade newsletter on SpaceX IPO readiness, not hype-only coverage.",
            required_dimensions=SPACE_X_DIMENSIONS,
            required_source_tiers={"primary": 4, "trusted_secondary": 3},
            required_visuals={"business_segment_map", "numbers_chart", "bull_bear_matrix", "timeline_or_listing_path"},
            min_hard_claims=6,
            final_score_minimum=88,
        )
    if "european" in topic_key and "bank" in topic_key:
        return ReportRubric(
            topic=topic,
            audience=audience,
            report_promise="Lightweight analyst-grade newsletter on European banking stress and policy mechanics.",
            required_dimensions=EUROPEAN_BANKING_DIMENSIONS,
            required_source_tiers={"primary": 5, "trusted_secondary": 4},
            required_visuals={"causal_map", "numbers_chart", "risk_matrix", "timeline"},
            min_hard_claims=6,
            final_score_minimum=88,
        )
    return ReportRubric(
        topic=topic,
        audience=audience,
        report_promise="Lightweight analyst-grade newsletter with grounded claims and modern visuals.",
        required_dimensions=GENERIC_DIMENSIONS,
        required_source_tiers={"primary": 3, "trusted_secondary": 2},
        required_visuals={"numbers_chart", "relationship_map", "bull_bear_matrix"},
    )


def evaluate_factory_gates(manifest: ReportRunManifest, evidence: EvidencePack, *, pages: list[PageMetrics]) -> FactoryGateResult:
    checks: list[FactoryGateCheck] = []
    checks.extend(_evidence_contract_checks(evidence))
    checks.extend(_research_coverage_checks(manifest.rubric, evidence))
    checks.extend(_synthesis_checks(manifest.rubric, evidence))
    checks.extend(_layout_checks(manifest.rubric, pages))

    route_back = _first_error_department(checks)
    score = max(0, 100 - 12 * len([check for check in checks if check.severity == "error"]) - 4 * len([check for check in checks if check.severity == "warning"]))
    return FactoryGateResult(ok=not any(check.severity == "error" for check in checks), score=score, checks=checks, route_back_department=route_back)


def _evidence_contract_checks(evidence: EvidencePack) -> list[FactoryGateCheck]:
    result = validate_evidence_pack(evidence)
    return [
        FactoryGateCheck(code=check.code, message=check.message, department=Department.ANALYSIS, severity=check.severity)
        for check in result.checks
    ]


def _research_coverage_checks(rubric: ReportRubric, evidence: EvidencePack) -> list[FactoryGateCheck]:
    predicates = {fact.predicate for fact in evidence.facts}
    checks: list[FactoryGateCheck] = []
    for dimension in rubric.required_dimensions:
        if dimension.required and f"dimension:{dimension.name}" not in predicates:
            checks.append(
                FactoryGateCheck(
                    code="missing_required_dimension",
                    message=f"Research coverage missing required dimension: {dimension.name}.",
                    department=Department.RESEARCH,
                )
            )
    return checks


def _synthesis_checks(rubric: ReportRubric, evidence: EvidencePack) -> list[FactoryGateCheck]:
    checks: list[FactoryGateCheck] = []
    hard_claims = [claim for claim in evidence.claims if _is_hard_hitting_claim(claim.text)]
    if len(hard_claims) < min(rubric.min_hard_claims, max(1, len(evidence.claims))):
        checks.append(
            FactoryGateCheck(
                code="weak_claim_density",
                message="Synthesis needs hard-hitting claim language: actor + mechanism + implication, preferably with numbers.",
                department=Department.SYNTHESIS,
            )
        )
    return checks


def _layout_checks(rubric: ReportRubric, pages: list[PageMetrics]) -> list[FactoryGateCheck]:
    checks: list[FactoryGateCheck] = []
    if rubric.require_source_appendix and not any(page.has_source_appendix for page in pages):
        checks.append(FactoryGateCheck(code="missing_source_appendix", message="Layout missing mandatory final source appendix page.", department=Department.LAYOUT))
    for page in pages:
        if page.fill_ratio < rubric.min_page_fill_ratio:
            checks.append(FactoryGateCheck(code="underfilled_page", message=f"Page {page.page_number} is underfilled for a lightweight report.", department=Department.LAYOUT))
        if page.overlap_count:
            checks.append(FactoryGateCheck(code="visual_overlap", message=f"Page {page.page_number} has {page.overlap_count} overlapping visual elements.", department=Department.LAYOUT))
        if page.clipped_text_count:
            checks.append(FactoryGateCheck(code="clipped_text", message=f"Page {page.page_number} has {page.clipped_text_count} clipped text boxes.", department=Department.LAYOUT))
    return checks


def _is_hard_hitting_claim(text: str) -> bool:
    words = text.split()
    if len(words) < 9:
        return False
    has_mechanism = any(marker in text.lower() for marker in ["because", "depends on", "drives", "through", "forces", "creates", "reduces", "raises"])
    has_specificity = any(char.isdigit() for char in text) or ";" in text or "," in text
    return has_mechanism and has_specificity


def _first_error_department(checks: list[FactoryGateCheck]) -> Department | None:
    priority = [Department.RESEARCH, Department.ANALYSIS, Department.SYNTHESIS, Department.VISUALS, Department.LAYOUT, Department.QA]
    error_departments = {check.department for check in checks if check.severity == "error"}
    for department in priority:
        if department in error_departments:
            return department
    return None
