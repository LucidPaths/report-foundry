"""CLI surfaces for planning, fixture research, validation, and rendering.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from time import perf_counter

import typer
from pydantic import ValidationError
from rich import print

from .adequacy import run_artifact_qa, run_research_adequacy_gates
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
from .run_log import FoundryRunLog, utc_now
from .samples import write_oss_strategy_report

app = typer.Typer(help="Evidence-contract, QA, and PDF packaging layer for authored research.")


@app.command("wizard")
def wizard(
    topic: str | None = typer.Option(None, "--topic", "-t", help="Research topic/request. Prompted when omitted."),
    audience: str | None = typer.Option(None, "--audience", "-a", help="Target reader. Prompted when omitted."),
    constraint: list[str] = typer.Option(default_factory=list, show_default=False, help="Research/source/output constraint. Repeatable."),
    out_dir: Path = typer.Option(Path(".foundry_wizard"), help="Directory for the research gate package."),
) -> None:
    """Write the prompt/schema package for a human or external report author."""
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
    print(f"[green]authoring prompt[/green] {prompt_path}")
    print(f"[green]intake target[/green] {intake_path}")
    print("next: give research_gate_prompt.md to the report author, save JSON to research_intake.json, then run:")
    print(f"uv run reportfoundry compile-intake {intake_path} --out-dir {out_dir / 'compiled'}")


def _research_gate_prompt(request_json: str) -> str:
    return f"""# Report Foundry research gate

You are entering Report Foundry's research contract. Foundry does not browse,
search, or decide facts here. A human or external report author supplies observed
sources, facts, claims, and prose; Foundry validates the structure and compiles
the artifact package.

Operator request:
```json
{request_json}
```

To pass through this contract:
- observe concrete sources before citing them;
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
    source: list[str] = typer.Option(default_factory=list, help="Connected source namespace, database, archive, or external source adapter."),
    run_mode: RunMode = typer.Option(RunMode.FIXTURE, help="Artifact governance mode: fixture, product, or experiment."),
) -> None:
    """Create a factory run package from a topic before research starts."""
    if integration_mode not in {"cli", "server", "library", "adapter"}:
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
    author: str = typer.Option("Research Author", help="Author label stored in the generated EvidencePack."),
) -> None:
    """Compile an authored Markdown draft into Foundry artifacts."""
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
    """Write the schema-only report authoring prompt used before EvidencePack normalization."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_research_intake_system_prompt(), encoding="utf-8")
    print(f"[green]research intake prompt[/green] {output}")


@app.command("compile-intake")
def compile_intake(input: Path, out_dir: Path = Path(".output_intake"), route: str = typer.Option("playwright_chromium", help="Renderer route: playwright_chromium, typst, pandoc, weasyprint, kaleido, or csl.")) -> None:
    """Compile strict ResearchIntake JSON into EvidencePack, ReportSpec, and package artifacts."""
    run_log = FoundryRunLog(run_id=out_dir.name or input.stem, topic=None, started_at=utc_now())
    try:
        evidence_path, paths = _compile_intake_to_artifacts(input, out_dir, route=route, run_log=run_log)
    except (IntakeValidationError, ValidationError, ValueError) as exc:
        run_log.finish(status="failed", error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]invalid research intake[/red]: {exc}")
        raise typer.Exit(1) from exc
    except RendererRouteError as exc:
        run_log.finish(status="failed", error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    run_log.artifacts.update(_artifact_strings(paths, extra={"evidence_pack": evidence_path}))
    run_log.add_step("final_handoff", details={"pdf": str(paths["pdf"]), "package_manifest": str(paths["package_manifest"])})
    run_log.finish(status="success", pdf=str(paths["pdf"]), package_manifest=str(paths["package_manifest"]))
    run_log.write(out_dir / "run_log.json")
    _print_final_handoff(paths, run_log_path=out_dir / "run_log.json")


@app.command("intake-run")
def intake_run(
    topic: str = typer.Option(..., "--topic", "-t", help="Keyword/topic for the intake contract."),
    intake_json: Path = typer.Option(..., help="Existing ResearchIntake JSON authored by a human or external authoring session."),
    out_dir: Path = typer.Option(Path(".foundry_runs/intake"), help="Run directory."),
    route: str = typer.Option("playwright_chromium", help="Renderer route."),
) -> None:
    """One-command ResearchIntake -> PDF/package loop.

    Foundry does not call a model, browse, search, or decide facts here. It loads
    a supplied ResearchIntake contract, validates it, compiles artifacts, runs QA,
    writes logs, and returns the package paths.
    """
    run_log = FoundryRunLog(run_id=out_dir.name or "intake-run", topic=topic, started_at=utc_now())
    gate_dir = out_dir / "gate"
    compiled_dir = out_dir / "compiled"
    gate_started, gate_perf = utc_now(), perf_counter()
    gate_dir.mkdir(parents=True, exist_ok=True)
    request = ResearchRequest(
        user_request=topic,
        topic=topic,
        core_question=topic,
        audience="unspecified",
        intended_use="professional evidence-backed report",
        depth="deep_research_report",
        format_preferences=["pdf"],
        explicit_constraints=["Use concrete observed sources; do not invent evidence"],
    )
    request_json = json.dumps(request.model_dump(), indent=2)
    (gate_dir / "research_request.json").write_text(request_json + "\n", encoding="utf-8")
    (gate_dir / "research_gate_prompt.md").write_text(_research_gate_prompt(request_json), encoding="utf-8")
    intake_path = gate_dir / "research_intake.json"
    shutil.copyfile(intake_json, intake_path)
    run_log.add_step("load_intake_contract", started_at=gate_started, started_perf=gate_perf, details={"source": str(intake_json), "target": str(intake_path), "prompt": str(gate_dir / "research_gate_prompt.md")})

    try:
        evidence_path, paths = _compile_intake_to_artifacts(intake_path, compiled_dir, route=route, run_log=run_log)
    except (IntakeValidationError, ValidationError, ValueError, RendererRouteError) as exc:
        run_log.finish(status="failed", topic=topic, error=str(exc))
        run_log.write(out_dir / "run_log.json")
        print(f"[red]intake-run failed[/red]: {exc}")
        raise typer.Exit(1) from exc

    verify_started, verify_perf = utc_now(), perf_counter()
    missing = [name for name in ("pdf", "html", "package_manifest") if not Path(paths[name]).exists()]
    if missing:
        run_log.add_step("verify_artifacts", status="error", started_at=verify_started, started_perf=verify_perf, details={"missing": missing})
        run_log.finish(status="failed", topic=topic, error=f"missing artifacts: {', '.join(missing)}")
        run_log.write(out_dir / "run_log.json")
        print(f"[red]intake-run failed[/red]: missing artifacts: {', '.join(missing)}")
        raise typer.Exit(1)
    run_log.add_step("verify_artifacts", started_at=verify_started, started_perf=verify_perf, details={"pdf": str(paths["pdf"]), "html": str(paths["html"])})
    run_log.artifacts.update(_artifact_strings(paths, extra={"evidence_pack": evidence_path}))
    run_log.add_step("final_handoff", details={"pdf": str(paths["pdf"]), "package_manifest": str(paths["package_manifest"])})
    run_log.finish(status="success", topic=topic, pdf=str(paths["pdf"]), package_manifest=str(paths["package_manifest"]))
    run_log.write(out_dir / "run_log.json")
    _print_final_handoff(paths, run_log_path=out_dir / "run_log.json")


def _compile_intake_to_artifacts(input: Path, out_dir: Path, *, route: str, run_log: FoundryRunLog) -> tuple[Path, dict[str, Path]]:
    validate_started, validate_perf = utc_now(), perf_counter()
    intake = ResearchIntake.model_validate_json(input.read_text(encoding="utf-8"))
    pack = research_intake_to_evidence_pack(intake)
    adequacy = run_research_adequacy_gates(intake)
    run_log.topic = run_log.topic or intake.request.topic
    run_log.add_step(
        "validate_intake",
        started_at=validate_started,
        started_perf=validate_perf,
        details={
            "sources": len(intake.sources),
            "facts": len(intake.facts),
            "claims": len(intake.proposed_claims),
            "sections": len(intake.report.sections),
            "exhibits": len(intake.exhibits),
            "adequacy_checks": [check.model_dump() for check in adequacy.checks],
        },
    )

    compile_started, compile_perf = utc_now(), perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = out_dir / f"{input.stem}.evidence.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    paths = write_spec_artifacts(pack, out_dir, stem=input.stem, route=route)
    artifact_qa = run_artifact_qa(paths)
    run_log.add_step(
        "compile_artifacts",
        started_at=compile_started,
        started_perf=compile_perf,
        details={"route": route, "pdf": str(paths["pdf"]), "html": str(paths["html"]), "package_manifest": str(paths["package_manifest"]), "artifact_qa_checks": [check.model_dump() for check in artifact_qa.checks]},
    )
    if not artifact_qa.ok:
        raise ValueError("artifact QA failed: " + ", ".join(check.code for check in artifact_qa.checks if check.severity == "error"))
    return evidence_path, paths


def _artifact_strings(paths: dict[str, Path], *, extra: dict[str, Path] | None = None) -> dict[str, str]:
    all_paths = {**paths, **(extra or {})}
    return {name: str(path) for name, path in all_paths.items()}


def _print_final_handoff(paths: dict[str, Path], *, run_log_path: Path) -> None:
    typer.echo("Here is your PDF")
    typer.echo("research intake: compiled")
    typer.echo(f"pdf: {paths['pdf']}")
    typer.echo(f"html: {paths['html']}")
    typer.echo(f"package manifest: {paths['package_manifest']}")
    typer.echo(f"run log: {run_log_path}")


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
