"""ExhibitSpec and Vega-Lite adapter tests.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims.
"""

from __future__ import annotations

import json
from pathlib import Path

from report_foundry.evidence import DraftExhibit, EvidenceClaim, EvidenceFact, EvidencePack, SourceObservation
from report_foundry.exhibit_adapters import VegaLiteExhibitAdapter, write_exhibit_artifacts
from report_foundry.exhibits import (
    ExhibitDataPoint,
    ExhibitKind,
    ExhibitSpec,
    exhibit_specs_from_evidence,
    validate_exhibit_specs,
)
from report_foundry.report_spec import compile_report_spec, compile_spec_to_report, write_spec_artifacts


def make_exhibit_pack() -> EvidencePack:
    source = SourceObservation(
        source_id="src_metrics",
        title="Fixture metrics",
        url="https://example.test/metrics",
        observed_at="2026-06-18T00:00:00Z",
        content_sha256="d" * 64,
        extractor="fixture",
    )
    facts = [
        EvidenceFact(
            fact_id="fact_revenue",
            subject="Segment A",
            predicate="metric:revenue",
            value="42",
            source_id=source.source_id,
            quote="Segment A revenue was 42 units.",
            locator="row 1",
        ),
        EvidenceFact(
            fact_id="fact_margin",
            subject="Segment B",
            predicate="metric:margin",
            value="17",
            source_id=source.source_id,
            quote="Segment B margin was 17 units.",
            locator="row 2",
        ),
    ]
    return EvidencePack(
        title="Exhibit fixture",
        scope={"run_mode": "product"},
        sources=[source],
        facts=facts,
        claims=[EvidenceClaim(text="Segment A and Segment B metrics are source-backed.", fact_ids=["fact_revenue", "fact_margin"], confidence="high")],
        exhibits=[
            DraftExhibit(
                visual_id="segment_metrics",
                visual_type="chart",
                title="Segment metrics",
                purpose="Compare source-backed segment metrics.",
                preferred_tool="vega_lite",
                provenance_fact_ids=["fact_revenue", "fact_margin"],
                plain_text_payload="Segment A: 42\nSegment B: 17",
            )
        ],
    )


def test_exhibit_without_fact_ids_fails_gate() -> None:
    spec = ExhibitSpec(
        exhibit_id="orphan_chart",
        title="Orphan chart",
        kind=ExhibitKind.CHART,
        insight="This chart has no provenance.",
        fact_ids=[],
        renderer_route="vega_lite",
        alt_text="Orphan chart.",
    )

    result = validate_exhibit_specs([spec], make_exhibit_pack())

    assert not result.ok
    assert any(check.code == "exhibit_missing_fact_ids" for check in result.checks)


def test_exhibit_with_unknown_fact_id_fails_gate() -> None:
    spec = ExhibitSpec(
        exhibit_id="unknown_fact_chart",
        title="Unknown fact chart",
        kind=ExhibitKind.CHART,
        insight="Unknown fact drives this chart.",
        fact_ids=["missing_fact"],
        data=[ExhibitDataPoint(label="Missing", value=1, fact_id="missing_fact")],
        renderer_route="vega_lite",
        alt_text="Unknown fact chart.",
    )

    result = validate_exhibit_specs([spec], make_exhibit_pack())

    assert not result.ok
    assert any(check.code == "exhibit_unknown_fact_id" for check in result.checks)
    assert any(check.code == "exhibit_data_unknown_fact_id" for check in result.checks)


def test_vega_lite_adapter_emits_json_with_data_values_tied_to_facts(tmp_path: Path) -> None:
    pack = make_exhibit_pack()
    spec = exhibit_specs_from_evidence(pack)[0]

    artifact = VegaLiteExhibitAdapter().render(spec, pack, tmp_path)

    payload = json.loads(Path(artifact.vega_json_path).read_text(encoding="utf-8"))
    assert artifact.route == "vega_lite"
    assert artifact.exhibit_id == "segment_metrics"
    assert artifact.alt_text == "Segment metrics: Compare source-backed segment metrics."
    assert payload["data"]["values"] == [
        {"label": "Segment A", "value": 42.0, "fact_id": "fact_revenue"},
        {"label": "Segment B", "value": 17.0, "fact_id": "fact_margin"},
    ]
    assert payload["encoding"]["x"]["field"] == "label"
    assert payload["encoding"]["y"]["field"] == "value"


def test_report_ir_includes_exhibit_artifact_paths_and_alt_text(tmp_path: Path) -> None:
    pack = make_exhibit_pack()
    paths = write_spec_artifacts(pack, tmp_path)

    assert "exhibits" in paths
    exhibits_manifest = json.loads(paths["exhibits"].read_text(encoding="utf-8"))
    assert exhibits_manifest["artifacts"][0]["vega_json_path"].endswith("segment_metrics.vega.json")

    spec = compile_report_spec(pack)
    artifacts = write_exhibit_artifacts(spec.exhibits, pack, tmp_path / "manual_exhibits")
    report = compile_spec_to_report(spec, {artifact.exhibit_id: Path(artifact.vega_json_path) for artifact in artifacts})

    figures = [block for section in report.sections for block in section.blocks if block.type == "figure"]
    assert any(figure.path == "segment_metrics.vega.json" and figure.alt_text == "Segment metrics: Compare source-backed segment metrics." for figure in figures)
