"""Built-in sample report workflows for exercising the full foundry pipeline.

Lattice: RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P6 Visuals Are Claims; RF-P8 Low Floor, High Ceiling.

These are executable fixtures, not hand-authored PDF shortcuts: they produce
EvidencePack objects and route through ReportSpec/render/QA like user reports.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .evidence import (
    EvidenceClaim,
    EvidenceFact,
    EvidencePack,
    ProfessionalKeyTakeaway,
    ProfessionalReportContent,
    ProfessionalReportSection,
    SourceObservation,
)
from .report_spec import write_spec_artifacts

REPOS: dict[str, str] = {
    "src_typst": "typst/typst",
    "src_quarto": "quarto-dev/quarto-cli",
    "src_pandoc": "jgm/pandoc",
    "src_weasyprint": "Kozea/WeasyPrint",
    "src_pagedjs": "pagedjs/pagedjs",
    "src_manubot": "manubot/manubot",
    "src_jupyter_book": "jupyter-book/jupyter-book",
    "src_citation_js": "citation-js/citation-js",
    "src_citeproc_js": "Juris-M/citeproc-js",
    "src_vega_lite": "vega/vega-lite",
    "src_mermaid": "mermaid-js/mermaid",
    "src_kaleido": "plotly/Kaleido",
    "src_dagster": "dagster-io/dagster",
    "src_snakemake": "snakemake/snakemake",
}

OFFLINE_REPO_METADATA: dict[str, dict[str, object]] = {
    "typst/typst": {"full_name": "typst/typst", "html_url": "https://github.com/typst/typst", "stargazers_count": 43000, "language": "Rust", "license": {"spdx_id": "Apache-2.0"}, "description": "A new markup-based typesetting system that is powerful and easy to learn."},
    "quarto-dev/quarto-cli": {"full_name": "quarto-dev/quarto-cli", "html_url": "https://github.com/quarto-dev/quarto-cli", "stargazers_count": 4900, "language": "TypeScript", "license": {"spdx_id": "GPL-2.0"}, "description": "Open-source scientific and technical publishing system."},
    "jgm/pandoc": {"full_name": "jgm/pandoc", "html_url": "https://github.com/jgm/pandoc", "stargazers_count": 37000, "language": "Haskell", "license": {"spdx_id": "GPL-2.0"}, "description": "Universal markup converter."},
    "Kozea/WeasyPrint": {"full_name": "Kozea/WeasyPrint", "html_url": "https://github.com/Kozea/WeasyPrint", "stargazers_count": 7000, "language": "Python", "license": {"spdx_id": "BSD-3-Clause"}, "description": "The awesome document factory."},
    "pagedjs/pagedjs": {"full_name": "pagedjs/pagedjs", "html_url": "https://github.com/pagedjs/pagedjs", "stargazers_count": 4700, "language": "JavaScript", "license": {"spdx_id": "MIT"}, "description": "Tools to paginate content in the browser to create PDF output from any HTML content."},
    "manubot/manubot": {"full_name": "manubot/manubot", "html_url": "https://github.com/manubot/manubot", "stargazers_count": 1000, "language": "Python", "license": {"spdx_id": "BSD-3-Clause"}, "description": "Manuscripts, open and automated."},
    "jupyter-book/jupyter-book": {"full_name": "jupyter-book/jupyter-book", "html_url": "https://github.com/jupyter-book/jupyter-book", "stargazers_count": 4100, "language": "Python", "license": {"spdx_id": "BSD-3-Clause"}, "description": "Create beautiful, publication-quality books and documents from computational content."},
    "citation-js/citation-js": {"full_name": "citation-js/citation-js", "html_url": "https://github.com/citation-js/citation-js", "stargazers_count": 850, "language": "JavaScript", "license": {"spdx_id": "MIT"}, "description": "Citation.js converts formats like BibTeX, Wikidata, and CSL-JSON."},
    "Juris-M/citeproc-js": {"full_name": "Juris-M/citeproc-js", "html_url": "https://github.com/Juris-M/citeproc-js", "stargazers_count": 300, "language": "JavaScript", "license": {"spdx_id": "AGPL-3.0"}, "description": "CSL citation processor."},
    "vega/vega-lite": {"full_name": "vega/vega-lite", "html_url": "https://github.com/vega/vega-lite", "stargazers_count": 5100, "language": "TypeScript", "license": {"spdx_id": "BSD-3-Clause"}, "description": "A concise grammar of interactive graphics."},
    "mermaid-js/mermaid": {"full_name": "mermaid-js/mermaid", "html_url": "https://github.com/mermaid-js/mermaid", "stargazers_count": 74000, "language": "JavaScript", "license": {"spdx_id": "MIT"}, "description": "Generation of diagrams like flowcharts or sequence diagrams from text."},
    "plotly/Kaleido": {"full_name": "plotly/Kaleido", "html_url": "https://github.com/plotly/Kaleido", "stargazers_count": 800, "language": "Python", "license": {"spdx_id": "MIT"}, "description": "Static image export for web-based visualization libraries."},
    "dagster-io/dagster": {"full_name": "dagster-io/dagster", "html_url": "https://github.com/dagster-io/dagster", "stargazers_count": 13000, "language": "Python", "license": {"spdx_id": "Apache-2.0"}, "description": "An orchestration platform for development, production, and observation of data assets."},
    "snakemake/snakemake": {"full_name": "snakemake/snakemake", "html_url": "https://github.com/snakemake/snakemake", "stargazers_count": 2400, "language": "Python", "license": {"spdx_id": "MIT"}, "description": "Workflow management system to create reproducible and scalable data analyses."},
}


def write_oss_strategy_report(out_dir: Path, *, offline: bool = False) -> dict[str, Path]:
    """Build the canonical OSS strategy sample through the full foundry pipeline."""

    out_dir.mkdir(parents=True, exist_ok=True)
    pack = build_oss_strategy_evidence_pack(offline=offline)
    evidence_path = out_dir / "oss_strategy_evidence_pack.json"
    evidence_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")
    paths = write_spec_artifacts(pack, out_dir, stem="oss_strategy_evidence_pack")
    return {"evidence_pack": evidence_path, **paths}


def build_oss_strategy_evidence_pack(*, offline: bool = False) -> EvidencePack:
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    repo_meta = _load_repo_metadata(offline=offline)
    sources = _sources(repo_meta, observed_at)
    facts = _facts(repo_meta)
    claims = [
        EvidenceClaim(text="Report Foundry should not build a bespoke PDF universe; it should become a provenance and orchestration layer over established rendering, citation, exhibit, and workflow systems.", fact_ids=["fact_report_foundry_ownership", "fact_typesetting_stack"], confidence="high"),
        EvidenceClaim(text="The first serious renderer spike should be Typst because it maps naturally from ProfessionalReportContent into high-polish PDF templates.", fact_ids=["fact_typst_viable", "fact_professional_schema"], confidence="medium"),
        EvidenceClaim(text="Citation handling needs its own adapter layer; source IDs and hashes are audit metadata, while Citation.js/citeproc-style outputs are reader-facing bibliography paths.", fact_ids=["fact_citation_layer", "fact_report_foundry_ownership"], confidence="high"),
        EvidenceClaim(text="Exhibits should be schema objects routed to specialized renderers: Vega-Lite for charts, Mermaid for diagrams, and Kaleido for static Plotly exports.", fact_ids=["fact_exhibit_layer", "fact_professional_schema"], confidence="high"),
        EvidenceClaim(text="Evidence collection should evolve into a reproducible asset/workflow graph instead of one-off scripts, with Dagster/Snakemake-style orchestration as prior art.", fact_ids=["fact_orchestration_layer", "fact_report_foundry_ownership"], confidence="medium"),
    ]
    return EvidencePack(
        title="Report Foundry OSS Strategy Brief",
        subtitle="Using open-source prior art to choose the next architecture seams",
        report_date=observed_at[:10],
        author="Report Foundry",
        scope={"audience": "product/engineering strategy readers", "format": "professional architecture brief"},
        sources=sources,
        facts=facts,
        claims=claims,
        professional_report=_professional_report(),
        tags=["oss-landscape", "report-foundry", "architecture", "professional-report"],
    )


def _load_repo_metadata(*, offline: bool) -> dict[str, dict[str, object]]:
    if offline:
        return {source_id: OFFLINE_REPO_METADATA[repo] for source_id, repo in REPOS.items()}
    return {source_id: _fetch_repo(repo) for source_id, repo in REPOS.items()}


def _fetch_repo(full_name: str) -> dict[str, object]:
    request = Request(
        f"https://api.github.com/repos/{full_name}",
        headers={"User-Agent": "ReportFoundry-OSS-Strategy-Report", "Accept": "application/vnd.github+json"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _sources(repo_meta: dict[str, dict[str, object]], observed_at: str) -> list[SourceObservation]:
    sources: list[SourceObservation] = []
    for source_id, data in repo_meta.items():
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        sources.append(
            SourceObservation(
                source_id=source_id,
                title=f"GitHub — {data['full_name']}",
                url=str(data["html_url"]),
                observed_at=observed_at,
                content_sha256=hashlib.sha256(payload).hexdigest(),
                extractor="github-rest-repository-metadata" if source_id in REPOS else "fixture",
                locator=f"stars={data.get('stargazers_count')}; language={data.get('language')}; license={((data.get('license') or {}) if isinstance(data.get('license'), dict) else {}).get('spdx_id')}",
            )
        )
    for path, source_id, title in [
        (Path("docs/DEVELOPER_HANDOFF_ROADMAP.md"), "src_repo_developer_handoff", "Report Foundry repo — developer handoff roadmap"),
        (Path("docs/PROFESSIONAL_REPORT_SCHEMA.md"), "src_repo_professional_schema", "Report Foundry repo — professional report schema doc"),
    ]:
        payload = path.read_bytes()
        sources.append(
            SourceObservation(source_id=source_id, title=title, url=str(path), observed_at=observed_at, content_sha256=hashlib.sha256(payload).hexdigest(), extractor="repo-file-read", locator=str(path))
        )
    return sources


def _desc(repo_meta: dict[str, dict[str, object]], source_id: str) -> str:
    data = repo_meta[source_id]
    license_id = ((data.get("license") or {}) if isinstance(data.get("license"), dict) else {}).get("spdx_id") or "NOASSERTION"
    return f"{data['full_name']} has {data.get('stargazers_count')} GitHub stars, primary language {data.get('language')}, license {license_id}, and description: {data.get('description')}"


def _facts(repo_meta: dict[str, dict[str, object]]) -> list[EvidenceFact]:
    desc = lambda source_id: _desc(repo_meta, source_id)
    return [
        EvidenceFact(fact_id="fact_typesetting_stack", subject="Report Foundry renderer strategy", predicate="formatting_prior_art", value="Typst, Quarto, Pandoc, WeasyPrint, and Playwright-class tools cover existing document rendering routes.", source_id="src_repo_developer_handoff", quote="Publishing/citation/exhibit tooling already exists and should become adapters, not rewritten internals: Pandoc, Typst, Quarto, CSL/citeproc, Citation.js, Vega-Lite, Mermaid, Kaleido, and Playwright.", locator="docs/DEVELOPER_HANDOFF_ROADMAP.md#prior-art-reality"),
        EvidenceFact(fact_id="fact_typst_viable", subject="Typst adapter", predicate="open_source_signal", value=desc("src_typst"), source_id="src_typst", quote=desc("src_typst"), locator="GitHub repository metadata"),
        EvidenceFact(fact_id="fact_report_foundry_ownership", subject="Report Foundry architecture boundary", predicate="design_principle", value="Report Foundry should own evidence/provenance/orchestration/QA and delegate layout/citation/exhibit machinery.", source_id="src_repo_developer_handoff", quote="Report Foundry should not become another deep-research system. Existing open-source systems already perform retrieval, query decomposition, multi-step research, RAG over documents, citation display, and Markdown/PDF report export.", locator="docs/DEVELOPER_HANDOFF_ROADMAP.md#purpose"),
        EvidenceFact(fact_id="fact_professional_schema", subject="Report Foundry content contract", predicate="design_principle", value="Professional reports require answer-first thesis, key takeaways, conclusion-led sections, so-what, limitations, and source URLs.", source_id="src_repo_professional_schema", quote="Professional reports are answer-first and evidence-backed: front matter, executive brief, conclusion-led sections, evidence body, exhibits, decision layer, and back matter.", locator="docs/PROFESSIONAL_REPORT_SCHEMA.md#structural-invariant"),
        EvidenceFact(fact_id="fact_citation_layer", subject="Citation strategy", predicate="prior_art", value="Citation.js and citeproc-js are citation/bibliography tooling candidates.", source_id="src_citation_js", quote=f"{desc('src_citation_js')} citeproc-js metadata was also observed as {desc('src_citeproc_js')}", locator="GitHub repository metadata"),
        EvidenceFact(fact_id="fact_exhibit_layer", subject="Exhibit strategy", predicate="prior_art", value="Vega-Lite, Mermaid, and Kaleido are exhibit rendering candidates.", source_id="src_vega_lite", quote=f"{desc('src_vega_lite')} Mermaid metadata was observed as {desc('src_mermaid')} Kaleido metadata was observed as {desc('src_kaleido')}", locator="GitHub repository metadata"),
        EvidenceFact(fact_id="fact_orchestration_layer", subject="Evidence pipeline strategy", predicate="prior_art", value="Dagster and Snakemake are workflow/orchestration candidates.", source_id="src_dagster", quote=f"{desc('src_dagster')} Snakemake metadata was also observed as {desc('src_snakemake')}", locator="GitHub repository metadata"),
    ]


def _professional_report() -> ProfessionalReportContent:
    return ProfessionalReportContent(
        one_sentence_thesis="Report Foundry should be an evidence/provenance operating system that delegates typesetting, citations, exhibits, and workflow execution to proven open-source systems instead of hand-rolling them.",
        executive_summary=[
            "The coded workflow now turns the previously manual sample process into a Foundry command. It creates a governed EvidencePack, compiles ReportSpec, renders Mermaid and Chromium outputs, and emits layout metrics for QA.",
            "The architecture implication remains direct: Foundry owns the evidence spine and adapters; mature external systems should own typesetting, bibliography rendering, chart rendering, and workflow execution.",
            "The next work should convert Typst, Citation.js/citeproc, Vega-Lite/Kaleido, and Dagster/Snakemake from roadmap entries into adapter interfaces with artifact-level regression tests.",
        ],
        key_takeaways=[
            ProfessionalKeyTakeaway(takeaway="Report Foundry’s durable moat is provenance and orchestration, not PDF layout code.", fact_ids=["fact_report_foundry_ownership", "fact_typesetting_stack"], implication="Renderer work should be adapter work."),
            ProfessionalKeyTakeaway(takeaway="Typst is the highest-value next renderer spike for polished PDF output.", fact_ids=["fact_typst_viable", "fact_professional_schema"], implication="It can turn ProfessionalReportContent into a high-design print contract without hand-editing PDFs."),
            ProfessionalKeyTakeaway(takeaway="Citations and exhibits need dedicated schemas before more design polish.", fact_ids=["fact_citation_layer", "fact_exhibit_layer"], implication="Without CSL/BibTeX and ExhibitSpec, the report remains structurally shallow."),
        ],
        sections=[
            ProfessionalReportSection(section_id="ownership_boundary", role="thesis", headline="The product boundary is evidence governance, not renderer ownership", lede="The open-source landscape is too strong to justify a bespoke formatting stack.", paragraphs=["Report Foundry should treat renderers, citation engines, chart engines, and workflow runners as replaceable muscles attached to a governed evidence spine.", "This division matches the current code: EvidencePack and ReportSpec separate observed evidence from renderer-neutral payloads, while compile-spec handles artifact routing and fail-closed QA."], fact_ids=["fact_report_foundry_ownership", "fact_professional_schema"], so_what="Prioritize schema and adapter seams over one-off visual tweaks.", limitations=["This sample uses GitHub metadata and repo docs, not benchmarked renderer comparisons."]),
            ProfessionalReportSection(section_id="renderer_stack", role="recommendations", headline="Renderer strategy should split polished print, interoperability, and pragmatic QA paths", lede="No single renderer should own the whole product.", paragraphs=["Typst is the best next spike for polished print templates. Pandoc and Quarto are interoperability routes for markdown and scientific publishing. WeasyPrint, Paged.js, and Playwright remain useful for CSS print workflows and automated visual QA.", "The same ProfessionalReportContent should be able to emit Typst, HTML/CSS, Quarto/Pandoc markdown, and QA screenshots without changing the upstream evidence package."], fact_ids=["fact_typesetting_stack", "fact_typst_viable"], so_what="Implement RendererAdapter contracts and start with a Typst adapter spike while keeping Playwright as the verification harness.", limitations=["Repository metadata indicates ecosystem viability, not final layout quality."]),
            ProfessionalReportSection(section_id="citations_exhibits", role="operating_analysis", headline="Citations and exhibits must become first-class schema objects", lede="Professional reports are not essays with links at the end.", paragraphs=["Citation.js and citeproc-js point to the right architecture: source metadata should normalize into citation objects and render through CSL/BibTeX-style outputs.", "The exhibit layer has the same shape. Vega-Lite should own charts, Mermaid should own diagrams, and Kaleido should own static Plotly exports; Foundry should define ExhibitSpec and validate provenance fact IDs."], fact_ids=["fact_citation_layer", "fact_exhibit_layer"], so_what="Build CitationAdapter and ExhibitSpec before adding more report templates.", limitations=["This sample proves Mermaid routing, not CSL/BibTeX or Vega/Kaleido output yet."]),
            ProfessionalReportSection(section_id="workflow_traceability", role="risk_analysis", headline="The research run needs a reproducible workflow log before it can scale", lede="Serious reports need a run history that explains what was searched, selected, rejected, transformed, and verified.", paragraphs=["Dagster and Snakemake show the direction: treat sources, extraction steps, facts, report sections, exhibits, renders, and QA outputs as graph artifacts.", "That run log would turn ad hoc sample scripts into repeatable research packages with inclusion/exclusion decisions and unresolved evidence gaps."], fact_ids=["fact_orchestration_layer", "fact_report_foundry_ownership"], so_what="Add ResearchRunLog beside EvidencePack/ReportSpec before scaling provider-backed research adapters.", limitations=["This command generates a sample report; it is not a full research workflow engine."]),
        ],
        what_to_watch=["Typst adapter spike", "CSL/BibTeX citation adapter", "ExhibitSpec with Vega-Lite and Kaleido", "ResearchRunLog for queries, candidates, included/rejected decisions, extractor hashes, and gaps"],
        methodology="Generated by Report Foundry's built-in OSS strategy sample workflow: EvidencePack construction, ReportSpec compilation, Mermaid visual rendering, Chromium PDF rendering, and PyMuPDF layout metrics.",
    )
