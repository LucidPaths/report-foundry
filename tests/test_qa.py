from report_foundry.ir import Claim, Report, Section
from report_foundry.qa import run_quality_gates


def test_quality_gate_flags_unsourced_claims():
    report = Report(title="Brief", sections=[Section(title="A", blocks=[Claim(text="Unsupported.")])])

    result = run_quality_gates(report)

    assert not result.ok
    assert result.checks[0].code == "unsupported_claim"
