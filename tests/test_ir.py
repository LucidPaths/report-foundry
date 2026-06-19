"""Semantic IR tests for claim/source traversal.

Lattice: RF-P2 Claim Traceability; RF-P3 Provider and Renderer Agnosticism.
"""

from report_foundry.ir import Citation, Claim, Report, Section, TextBlock


def test_report_collects_claims_and_citations():
    citation = Citation(source_id="src_context_window", url="https://example.com", quote="large-context workflow evidence")
    claim = Claim(text="The system supports a large-context source workflow.", citations=[citation])
    report = Report(
        title="Daily Systems Brief",
        sections=[Section(title="Models", blocks=[TextBlock(text="Signal."), claim])],
    )

    assert report.claims()[0].text == "The system supports a large-context source workflow."
    assert report.sources()[0].source_id == "src_context_window"
