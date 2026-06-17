from report_foundry.ir import Citation, Claim, Report, Section, TextBlock


def test_report_collects_claims_and_citations():
    citation = Citation(source_id="src_glm", url="https://example.com", quote="solid 1M context")
    claim = Claim(text="GLM supports a 1M-token context.", citations=[citation])
    report = Report(
        title="Daily Systems Brief",
        sections=[Section(title="Models", blocks=[TextBlock(text="Signal."), claim])],
    )

    assert report.claims()[0].text == "GLM supports a 1M-token context."
    assert report.sources()[0].source_id == "src_glm"
