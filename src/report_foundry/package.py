"""Run package manifest contracts.

Lattice: RF-P3 Provider and Renderer Agnosticism; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .factory import RunMode


class PackageArtifact(BaseModel):
    key: str
    path: str
    kind: str
    exists: bool


class PackageManifest(BaseModel):
    package_id: str
    route: str
    run_mode: RunMode
    status: Literal["success", "failed"]
    artifacts: dict[str, PackageArtifact]
    gates: dict[str, str] = Field(default_factory=dict)
    source_paths: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def build_package_manifest(
    *,
    package_id: str,
    route: str,
    run_mode: RunMode,
    status: Literal["success", "failed"],
    out_dir: Path,
    artifact_paths: dict[str, Path],
    gates: dict[str, Path],
    source_paths: list[Path],
    errors: list[str] | None = None,
) -> PackageManifest:
    artifacts = {
        key: PackageArtifact(
            key=key,
            path=_relative(path, out_dir),
            kind=_kind(key, path),
            exists=path.exists(),
        )
        for key, path in artifact_paths.items()
    }
    return PackageManifest(
        package_id=package_id,
        route=route,
        run_mode=run_mode,
        status=status,
        artifacts=artifacts,
        gates={key: _relative(path, out_dir) for key, path in gates.items()},
        source_paths=[_relative(path, out_dir) for path in source_paths if path.exists()],
        errors=errors or [],
    )


def write_package_manifest(manifest: PackageManifest, path: Path) -> Path:
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _kind(key: str, path: Path) -> str:
    if key in {"render_gate_result"} or key.endswith("gate_result"):
        return "gate"
    if key in {"evidence_pack", "spec", "ir", "citations", "csl", "bibtex", "source_appendix", "exhibits", "render_artifact"}:
        return "data"
    if path.suffix.lower() in {".html", ".pdf", ".svg", ".png", ".mmd"} or path.is_dir():
        return "rendered"
    return "artifact"
