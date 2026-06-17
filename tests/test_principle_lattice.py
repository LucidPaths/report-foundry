"""Principle-lattice doctrine tests.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DOCTRINE_PATHS = [ROOT / "src", ROOT / "scripts", ROOT / "tests"]
PRINCIPLE_NAMES = {
    "RF-P1": "Source Sovereignty",
    "RF-P2": "Claim Traceability",
    "RF-P3": "Provider and Renderer Agnosticism",
    "RF-P4": "Gates Fail Closed",
    "RF-P5": "Case Law Before Generation",
    "RF-P6": "Visuals Are Claims",
    "RF-P7": "Secrets Stay Handles",
    "RF-P8": "Low Floor, High Ceiling",
}
LATTICE_LINE = re.compile(r"^Lattice:\s*(?P<declaration>.+)$", re.MULTILINE)
PRINCIPLE_DECLARATION = re.compile(r"\b(RF-P[1-8])\s+([^;.]+)")


def test_principle_lattice_doctrine_exists_and_names_all_principles() -> None:
    doctrine = (ROOT / "docs" / "PRINCIPLE_LATTICE.md").read_text(encoding="utf-8")

    for code, name in PRINCIPLE_NAMES.items():
        assert f"{code}. {name}" in doctrine

    assert "Lattice:" in doctrine
    assert "A principle without an instantiation is a wish" in doctrine


def test_agent_instructions_mirror_hivemind_lattice_operating_layer() -> None:
    instructions = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "## Principle Lattice" in instructions
    assert "## Pre-Commit Verification" in instructions
    assert "## Things to Avoid" in instructions
    assert "docs/PRINCIPLE_LATTICE.md" in instructions
    assert "Lattice:" in instructions

    for code, name in PRINCIPLE_NAMES.items():
        assert code in instructions
        assert name in instructions

    for required_check in [
        "Run the full suite",
        "Trace the actual flow",
        "Grep for the pattern",
        "Check all 8 Principle Lattice items explicitly",
        "No dead code",
        "Check external-surface safety",
        "Inspect the diff",
    ]:
        assert required_check in instructions


def test_lattice_parser_rejects_empty_unknown_duplicate_and_misnamed_declarations() -> None:
    assert _parse_lattice_principles("Lattice: RF-P1 Source Sovereignty.") == ["RF-P1"]

    for invalid_docstring in [
        "Lattice:",
        "Lattice: vibes",
        "Lattice: RF-P9 Unknown Principle.",
        "Lattice: RF-P1 Wrong Name.",
        "Lattice: RF-P1 Source Sovereignty; RF-P1 Source Sovereignty.",
    ]:
        try:
            _parse_lattice_principles(invalid_docstring)
        except AssertionError:
            continue
        raise AssertionError(f"invalid lattice declaration passed: {invalid_docstring}")


def test_python_files_declare_canonical_lattice_notation() -> None:
    invalid: list[str] = []
    for base_path in PYTHON_DOCTRINE_PATHS:
        for path in sorted(base_path.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"))
            docstring = ast.get_docstring(module) or ""
            try:
                _parse_lattice_principles(docstring)
            except AssertionError as exc:
                invalid.append(f"{path.relative_to(ROOT)}: {exc}")

    assert invalid == []


def _parse_lattice_principles(docstring: str) -> list[str]:
    match = LATTICE_LINE.search(docstring)
    assert match, "missing Lattice declaration"

    declaration = match.group("declaration").strip()
    assert declaration, "empty Lattice declaration"

    parsed = PRINCIPLE_DECLARATION.findall(declaration)
    assert parsed, "no canonical RF-P principle declarations found"

    codes = [code for code, _name in parsed]
    assert len(codes) == len(set(codes)), "duplicate RF-P principle declaration"

    unknown_codes = sorted(set(re.findall(r"RF-P\d+", declaration)) - set(PRINCIPLE_NAMES))
    assert not unknown_codes, f"unknown principle codes: {', '.join(unknown_codes)}"

    for code, name in parsed:
        expected_name = PRINCIPLE_NAMES[code]
        assert name.strip() == expected_name, f"{code} must be named {expected_name!r}, got {name.strip()!r}"

    return codes
