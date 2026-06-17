"""Principle-lattice doctrine tests.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DOCTRINE_PATHS = [ROOT / "src", ROOT / "scripts", ROOT / "tests"]


def test_principle_lattice_doctrine_exists_and_names_all_principles() -> None:
    doctrine = (ROOT / "docs" / "PRINCIPLE_LATTICE.md").read_text(encoding="utf-8")

    for principle in [
        "RF-P1. Source Sovereignty",
        "RF-P2. Claim Traceability",
        "RF-P3. Provider and Renderer Agnosticism",
        "RF-P4. Gates Fail Closed",
        "RF-P5. Case Law Before Generation",
        "RF-P6. Visuals Are Claims",
        "RF-P7. Secrets Stay Handles",
        "RF-P8. Low Floor, High Ceiling",
    ]:
        assert principle in doctrine

    assert "Lattice:" in doctrine
    assert "A principle without an instantiation is a wish" in doctrine


def test_python_files_declare_lattice_notation() -> None:
    missing: list[str] = []
    for base_path in PYTHON_DOCTRINE_PATHS:
        for path in sorted(base_path.rglob("*.py")):
            module = ast.parse(path.read_text(encoding="utf-8"))
            docstring = ast.get_docstring(module) or ""
            if "Lattice:" not in docstring:
                missing.append(str(path.relative_to(ROOT)))

    assert missing == []
