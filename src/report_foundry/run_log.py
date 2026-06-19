"""Structured per-run logs for Report Foundry E2E runs.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

StepStatus = Literal["ok", "error", "skipped"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RunLogStep(BaseModel):
    name: str
    status: StepStatus
    started_at: str
    finished_at: str
    duration_ms: int
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FoundryRunLog(BaseModel):
    run_id: str
    topic: str | None = None
    model: str | None = None
    started_at: str
    finished_at: str | None = None
    steps: list[RunLogStep] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)

    def add_step(self, name: str, *, status: StepStatus = "ok", message: str | None = None, details: dict[str, Any] | None = None, started_at: str | None = None, started_perf: float | None = None) -> None:
        started = started_at or utc_now()
        duration_ms = int((perf_counter() - started_perf) * 1000) if started_perf is not None else 0
        self.steps.append(
            RunLogStep(
                name=name,
                status=status,
                started_at=started,
                finished_at=utc_now(),
                duration_ms=duration_ms,
                message=message,
                details=details or {},
            )
        )

    def finish(self, *, status: str = "success", **summary: Any) -> None:
        self.finished_at = utc_now()
        self.summary = {"status": status, **summary}

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path
