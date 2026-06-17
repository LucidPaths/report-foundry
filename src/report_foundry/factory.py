"""Analyst-factory contracts for rubrics, source plans, visual plans, and route-back gates.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P5 Case Law Before Generation; RF-P6 Visuals Are Claims; RF-P7 Secrets Stay Handles.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
FoundryPipelineStage = Literal[
    "keyword_intake",
    "ai_search",
    "source_observation",
    "fact_extraction",
    "claim_synthesis",
    "visual_layout",
    "qa_export",
]


class ConnectedProvider(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    api_key_env_var: str

    @field_validator("provider", "api_key_env_var")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider connection fields must not be empty")
        return value


class FoundryRunRequest(BaseModel):
    """Top-level product intake: user key reference + keyword/topic enters the foundry."""

    model_config = ConfigDict(extra="forbid")

    keyword: str
    ai: ConnectedProvider
    search: ConnectedProvider
    audience: str = "executive readers"
    pipeline: list[FoundryPipelineStage] = Field(
        default_factory=lambda: [
            "keyword_intake",
            "ai_search",
            "source_observation",
            "fact_extraction",
            "claim_synthesis",
            "visual_layout",
            "qa_export",
        ]
    )

    @field_validator("keyword", "audience")
    @classmethod
    def text_fields_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("foundry intake text fields must not be empty")
        return value


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


class SourcePlanItem(BaseModel):
    dimension: str
    purpose: str
    required_source_tiers: dict[str, int] = Field(default_factory=dict)
    source_hints: list[str] = Field(default_factory=list)
    acceptance_rule: str


class SourcePlan(BaseModel):
    topic: str
    items: list[SourcePlanItem]


class VisualPlanItem(BaseModel):
    visual_id: str
    purpose: str
    visual_type: Literal["chart", "map", "matrix", "timeline", "diagram"]
    provenance_required: bool = True
    acceptance_rule: str


class VisualPlan(BaseModel):
    topic: str
    items: list[VisualPlanItem]


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


class RunPackage(BaseModel):
    run_dir: Path
    manifest: ReportRunManifest
    source_plan: SourcePlan
    visual_plan: VisualPlan
    initial_gate_result: FactoryGateResult


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


def build_foundry_run_request(
    *,
    keyword: str,
    ai_provider: str,
    ai_api_key_env_var: str,
    search_provider: str | None = None,
    search_api_key_env_var: str | None = None,
    audience: str = "executive readers",
) -> FoundryRunRequest:
    return FoundryRunRequest(
        keyword=keyword,
        audience=audience,
        ai=ConnectedProvider(provider=ai_provider, api_key_env_var=ai_api_key_env_var),
        search=ConnectedProvider(
            provider=search_provider or ai_provider,
            api_key_env_var=search_api_key_env_var or ai_api_key_env_var,
        ),
    )


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


def build_source_plan(rubric: ReportRubric) -> SourcePlan:
    return SourcePlan(
        topic=rubric.topic,
        items=[
            SourcePlanItem(
                dimension=dimension.name,
                purpose=dimension.description,
                required_source_tiers=_source_tier_quota(rubric),
                source_hints=_source_hints_for_dimension(dimension.name),
                acceptance_rule="At least one primary or trusted source observation must produce facts for this dimension.",
            )
            for dimension in rubric.required_dimensions
            if dimension.required
        ],
    )


def build_visual_plan(rubric: ReportRubric) -> VisualPlan:
    return VisualPlan(
        topic=rubric.topic,
        items=[
            VisualPlanItem(
                visual_id=visual_id,
                purpose=_visual_purpose(visual_id),
                visual_type=_visual_type(visual_id),
                acceptance_rule="Visual must cite source-backed data or source-backed relationship claims; decorative visuals fail QA.",
            )
            for visual_id in sorted(rubric.required_visuals)
        ],
    )


def write_run_package(
    *,
    topic: str,
    audience: str,
    out_dir: Path,
    integration_mode: Literal["cli", "mcp", "server", "library"] = "cli",
    connected_sources: list[str] | None = None,
) -> RunPackage:
    rubric = build_case_rubric(topic, audience=audience)
    manifest = ReportRunManifest(
        topic=topic,
        rubric=rubric,
        integration_mode=integration_mode,
        connected_sources=connected_sources or [],
    )
    source_plan = build_source_plan(rubric)
    visual_plan = build_visual_plan(rubric)
    empty_evidence = EvidencePack(title=topic, scope={"status": "planning_only_no_sources_observed_yet"})
    initial_gate_result = evaluate_factory_gates(
        manifest,
        empty_evidence,
        pages=[PageMetrics(page_number=1, fill_ratio=0.0, has_source_appendix=False)],
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(out_dir / "rubric.json", rubric)
    _write_json(out_dir / "source_plan.json", source_plan)
    _write_json(out_dir / "visual_plan.json", visual_plan)
    _write_json(out_dir / "initial_gate_result.json", initial_gate_result)
    return RunPackage(run_dir=out_dir, manifest=manifest, source_plan=source_plan, visual_plan=visual_plan, initial_gate_result=initial_gate_result)


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


def _source_tier_quota(rubric: ReportRubric) -> dict[str, int]:
    primary = 1 if rubric.required_source_tiers.get("primary", 0) else 0
    trusted = 1 if rubric.required_source_tiers.get("trusted_secondary", 0) else 0
    return {"primary": primary, "trusted_secondary": trusted}


def _source_hints_for_dimension(dimension: str) -> list[str]:
    hints_by_keyword = {
        "starlink": ["company metrics or filings", "subscriber/revenue disclosures", "trusted telecom market data"],
        "government": ["government contract database", "NASA or defense procurement source", "company disclosures"],
        "launch": ["launch manifest", "payload registry", "regulator or operator records"],
        "listing": ["exchange rule filing", "securities regulator source", "issuer/listing documentation"],
        "valuation": ["private market transaction data", "comparable public-company filings", "trusted market data provider"],
        "covid": ["central bank balance-sheet data", "fiscal authority data", "statistical agency source"],
        "sovereign": ["treasury/debt office data", "central bank data", "government budget documents"],
        "gold": ["central bank reserve data", "IMF reserve statistics", "official FX reserve reports"],
        "regulatory": ["law text", "regulator guidance", "official consultation paper"],
        "credit": ["bank filings", "supervisory data", "real-estate credit statistics"],
        "ecb": ["ECB data", "national central bank data", "sovereign spread data"],
    }
    normalized = dimension.lower()
    for keyword, hints in hints_by_keyword.items():
        if keyword in normalized:
            return hints
    return ["primary source", "trusted secondary source", "dataset or official documentation"]


def _visual_type(visual_id: str) -> Literal["chart", "map", "matrix", "timeline", "diagram"]:
    if "chart" in visual_id:
        return "chart"
    if "map" in visual_id:
        return "map"
    if "matrix" in visual_id:
        return "matrix"
    if "timeline" in visual_id or "listing_path" in visual_id:
        return "timeline"
    return "diagram"


def _visual_purpose(visual_id: str) -> str:
    purposes = {
        "business_segment_map": "Show how business segments, funding channels, and risk drivers relate.",
        "numbers_chart": "Compress the report's core numeric evidence into one readable chart.",
        "bull_bear_matrix": "Make the strongest hype case and skeptic case comparable on one page.",
        "timeline_or_listing_path": "Show sequencing, regulatory path, and key timing dependencies.",
        "causal_map": "Show cause-and-effect relationships across policy, markets, and balance sheets.",
        "risk_matrix": "Compare likelihood and impact of major risks without dense prose.",
        "timeline": "Show the order of policy, market, and legal changes.",
        "relationship_map": "Show actors, incentives, dependencies, and bottlenecks.",
    }
    return purposes.get(visual_id, f"Explain {visual_id.replace('_', ' ')} visually with sourced evidence.")


def _write_json(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _first_error_department(checks: list[FactoryGateCheck]) -> Department | None:
    priority = [Department.RESEARCH, Department.ANALYSIS, Department.SYNTHESIS, Department.VISUALS, Department.LAYOUT, Department.QA]
    error_departments = {check.department for check in checks if check.severity == "error"}
    for department in priority:
        if department in error_departments:
            return department
    return None
