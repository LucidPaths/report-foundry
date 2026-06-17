"""Autonomy worker-plan tests for HIVE-style coordinator/scratchpad execution topology.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json

from report_foundry.factory import build_autonomy_plan, build_case_rubric, build_source_plan, build_visual_plan, write_run_package


def test_autonomy_plan_turns_source_and_visual_plans_into_worker_tasks() -> None:
    rubric = build_case_rubric("current SpaceX IPO launch newsletter", audience="executive readers")
    source_plan = build_source_plan(rubric)
    visual_plan = build_visual_plan(rubric)

    plan = build_autonomy_plan(topic=rubric.topic, source_plan=source_plan, visual_plan=visual_plan)

    assert plan.scratchpad_id.startswith("report-foundry-")
    assert plan.workspace_policy == "isolated_run_directory"
    assert plan.notification_policy == "worker completion emits compact status plus scratchpad section pointer"

    research_tasks = [task for task in plan.tasks if task.department == "research"]
    assert len(research_tasks) == len(source_plan.items)
    assert any(task.worker_id == "research-starlink-economics" for task in research_tasks)
    assert all(task.scratchpad_section.startswith("research/") for task in research_tasks)
    assert all("source_plan.json" in task.inputs for task in research_tasks)
    assert all("token_delta_or_file_output" in task.health_checks for task in research_tasks)

    synthesis = next(task for task in plan.tasks if task.worker_id == "synthesis-claims")
    assert {task.worker_id for task in research_tasks} <= set(synthesis.depends_on)
    assert synthesis.scratchpad_section == "synthesis/claims"

    visual_tasks = [task for task in plan.tasks if task.department == "visuals"]
    assert {task.worker_id for task in visual_tasks} >= {"visuals-business-segment-map", "visuals-numbers-chart", "visuals-bull-bear-matrix"}
    assert all("synthesis-claims" in task.depends_on for task in visual_tasks)

    qa = plan.tasks[-1]
    assert qa.worker_id == "qa-final-gates"
    assert qa.department == "qa"
    assert "research_gate_result.json" in qa.outputs


def test_write_run_package_persists_worker_plan(tmp_path) -> None:
    out_dir = tmp_path / "run"

    package = write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=out_dir)

    assert (out_dir / "worker_plan.json").exists()
    worker_plan = json.loads((out_dir / "worker_plan.json").read_text(encoding="utf-8"))
    assert worker_plan["scratchpad_id"] == package.worker_plan.scratchpad_id
    assert any(task["worker_id"] == "research-starlink-economics" for task in worker_plan["tasks"])
    assert any(task["worker_id"] == "qa-final-gates" for task in worker_plan["tasks"])
