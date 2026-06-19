"""CLI surfaces for planning, fixture research, validation, and rendering.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError
from rich import print

from .draft import parse_markdown_draft_file
from .factory import RunMode, write_run_package
from .ir import Report
from .evidence import EvidencePack
from .qa import run_quality_gates
from .research import write_research_artifacts
from .research_intake import IntakeValidationError, ResearchIntake, ResearchRequest, build_research_intake_system_prompt, research_intake_to_evidence_pack
from .render import render_html, render_pdf
from .renderers import RendererRouteError
from .report_spec import write_spec_artifacts
from .samples import write_oss_strategy_report

app = typer.Typer(help="AI-native evidence-to-PDF report compiler.")


@app.command("wizard")
def wizard(
    topic: str | None = typer.Option(None, "--topic", "-t", help="Research topic/request. Prompted when omitted."),
    audience: str | None = typer.Option(None, "--audience", "-a", help="Target reader. Prompted when omitted."),
    constraint: list[str] = typer.Option(default_factory=list, show_default=False, help="Research/source/output constraint. Repeatable."),
    out_dir: Path = typer.Option(Path(".foundry_wizard"), help="Directory for the research gate package."),
) -> None:
    """Open the research gate: collect a topic and write the LLM intake package."""
    if topic is None:
        topic = typer.prompt("Research topic")
    if audience is None:
        audience = typer.prompt("Audience", default="executive readers")
    if not constraint:
        entered_constraint = typer.prompt("Research constraint", default="Use concrete observed sources; do not invent evidence")
        constraint = [entered_constraint] if entered_constraint.strip() else []

    request = ResearchRequest(
        user_request=topic,
        topic=topic,
        core_question=topic,
        audience=audience,
        intended_use="professional evidence-backed report",
        depth="deep_research_report",
        format_preferences=["pdf"],
        explicit_constraints=constraint,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    request_path = out_dir / "research_request.json"
    prompt_path = out_dir / "research_gate_prompt.md"
    intake_path = out_dir / "research_intake.json"

    request_json = json.dumps(request.model_dump(), indent=2)
    request_path.write_text(request_json + "\n", encoding="utf-8")
    prompt_path.write_text(_research_gate_prompt(request_json), encoding="utf-8")
    intake_path.write_text("PASTE_RESEARCH_INTAKE_JSON_HERE\n", encoding="utf-8")

    print(f"[green]research gate[/green] {out_dir}")
    print(f"[green]request[/green] {request_path}")
    print(f"[green]llm prompt[/green] {prompt_path}")
    print(f"[green]intake target[/green] {intake_path}")
    print("next: give research_gate_prompt.md to the research LLM, save JSON to research_intake.json, then run:")
    print(f"uv run reportfoundry compile-intake {intake_path} --out-dir {out_dir / 'compiled'}")


def _research_gate_prompt(request_json: str) -> str:
    return f"""# Report Foundry research gate

You are entering Report Foundry. This CLI door is a research gate, not a casual chat prompt.

Operator request:
```json
{request_json}
```

To pass through this door:
- research the operator request using concrete observed sources;
- Do not invent sources, quotes, URLs, facts, claims, or citations;
- write the full report inside the ResearchIntake JSON schema;
- every claim must reference supporting fact IDs;
- every fact must reference an observed source and quote/excerpt;
- return only valid JSON matching the schema below.

{build_research_intake_system_prompt()}
"""


@app.command("plan-run")
def plan_run(
    topic: str,
    audience: str = "executive readers",
    out_dir: Path = Path(".factory-run"),
    integration_mode: str = "cli",
    source: list[str] = typer.Option(default_factory=list, help="Connected source namespace, MCP tool, database, or web connector."),
    run_mode: RunMode = typer.Option(RunMode.FIXTURE, help="Artifact governance mode: fixture, product, or experiment."),
) -> None:
    """Create a factory run package from a topic before research starts."""
    if integration_mode not in {"cli", "mcp", "server", "library"}:
        print(f"[red]invalid integration mode[/red]: {integration_mode}")
        raise typer.Exit(1)
    package = write_run_package(
        topic=topic,
        audience=audience,
        out_dir=out_dir,
        integration_mode=integration_mode,  # type: ignore[arg-type]
        connected_sources=source,
        run_mode=run_mode,
    )
    print(f"[green]factory run package[/green] {package.run_dir}")
    print(f"mode={package.manifest.run_mode.value}")
    print(f"route_back={package.initial_gate_result.route_back_department or 'none'} score={package.initial_gate_result.score}")


@app.command("research-run")
def research_run(
    run_dir: Path,
    source_dir: Path = typer.Option(..., help="Directory containing .md/.txt marked source files."),
    allow_fixture_sources: bool = typer.Option(False, help="Allow local marked sources even when manifest.run_mode is product."),
) -> None:
    """Fixture adapter: extract evidence from local marked sources."""
    try:
        result = write_research_artifacts(run_dir=run_dir, source_dir=source_dir, allow_fixture_sources=allow_fixture_sources)
    except ValueError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print(f"[green]research evidence[/green] {run_dir / 'evidence_pack.json'}")
    print(f"mode={result.manifest.run_mode.value}")
    print(f"route_back={result.gate_result.route_back_department or 'none'} score={result.gate_result.score}")
    if not result.gate_result.ok:
        raise typer.Exit(1)


@app.command("compile-draft")
def compile_draft(
    input: Path,
    out_dir: Path = Path(".output_draft"),
    author: str = typer.Option("Research LLM", help="Author label stored in the generated EvidencePack."),
) -> None:
    """Compile an LLM-authored Markdown draft into Foundry artifacts."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pack = parse_markdown_draft_file(input, author=author)
    evidence_path = out_dir / f"{input.stem}.evidence.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    paths = write_spec_artifacts(pack, out_dir, stem=input.stem)
    print(f"[green]evidence pack[/green] {evidence_path}")
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]package manifest[/green] {paths['package_manifest']}")
    print(f"[green]layout metrics[/green] {paths['layout_metrics']}")
    print(f"[green]page previews[/green] {paths['page_previews']}")


@app.command("compile-spec")
def compile_spec(input: Path, out_dir: Path = Path(".output_spec"), route: str = typer.Option("playwright_chromium", help="Renderer route: playwright_chromium, typst, or pandoc.")) -> None:
    """Compile an EvidencePack into strict ReportSpec, IR, HTML, and PDF artifacts."""
    pack = EvidencePack.model_validate_json(input.read_text(encoding="utf-8"))
    try:
        paths = write_spec_artifacts(pack, out_dir, stem=input.stem, route=route)
    except RendererRouteError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]route[/green]={route}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]package manifest[/green] {paths['package_manifest']}")


@app.command("research-intake-prompt")
def research_intake_prompt(output: Path = typer.Option(..., help="Path to write the strict research-intake system prompt.")) -> None:
    """Write the schema-only LLM researcher prompt used before EvidencePack normalization."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_research_intake_system_prompt(), encoding="utf-8")
    print(f"[green]research intake prompt[/green] {output}")


@app.command("compile-intake")
def compile_intake(input: Path, out_dir: Path = Path(".output_intake"), route: str = typer.Option("playwright_chromium", help="Renderer route: playwright_chromium, typst, or pandoc.")) -> None:
    """Compile strict LLM ResearchIntake JSON into EvidencePack, ReportSpec, and package artifacts."""
    try:
        intake = ResearchIntake.model_validate_json(input.read_text(encoding="utf-8"))
        pack = research_intake_to_evidence_pack(intake)
        out_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = out_dir / f"{input.stem}.evidence.json"
        evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        paths = write_spec_artifacts(pack, out_dir, stem=input.stem, route=route)
    except (IntakeValidationError, ValidationError, ValueError) as exc:
        print(f"[red]invalid research intake[/red]: {exc}")
        raise typer.Exit(1) from exc
    except RendererRouteError as exc:
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print(f"[green]research intake[/green] {input}")
    print(f"[green]evidence pack[/green] {evidence_path}")
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]route[/green]={route}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]package manifest[/green] {paths['package_manifest']}")


@app.command("oss-strategy-report")
def oss_strategy_report(
    out_dir: Path = Path(".output_oss_strategy"),
    offline: bool = typer.Option(False, help="Use packaged repository metadata instead of live GitHub API calls."),
) -> None:
    """Build the canonical OSS strategy sample through the full foundry pipeline."""
    paths = write_oss_strategy_report(out_dir, offline=offline)
    print(f"[green]evidence pack[/green] {paths['evidence_pack']}")
    print(f"[green]report spec[/green] {paths['spec']}")
    print(f"[green]built[/green] {paths['html']}")
    print(f"[green]built[/green] {paths['pdf']}")
    print(f"[green]package manifest[/green] {paths['package_manifest']}")
    print(f"[green]layout metrics[/green] {paths['layout_metrics']}")
    print(f"[green]page previews[/green] {paths['page_previews']}")


@app.command()
def build(input: Path, out_dir: Path = Path(".output")) -> None:
    """Build HTML and PDF from a Report Foundry JSON report."""
    report = Report.model_validate_json(input.read_text(encoding="utf-8"))
    qa = run_quality_gates(report)
    if not qa.ok:
        for check in qa.checks:
            print(f"[red]{check.code}[/red]: {check.message} ({check.location})")
        raise typer.Exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{input.stem}.html"
    pdf_path = out_dir / f"{input.stem}.pdf"
    html_path.write_text(render_html(report), encoding="utf-8")
    render_pdf(report, pdf_path)
    print(f"[green]built[/green] {html_path}")
    print(f"[green]built[/green] {pdf_path}")


@app.command()
def validate(input: Path) -> None:
    """Run report-level quality gates against JSON IR."""
    report = Report.model_validate_json(input.read_text(encoding="utf-8"))
    result = run_quality_gates(report)
    for check in result.checks:
        color = "red" if check.severity == "error" else "yellow"
        print(f"[{color}]{check.severity} {check.code}[/{color}]: {check.message} {check.location or ''}")
    if not result.ok:
        raise typer.Exit(1)
    print("[green]ok[/green]")
