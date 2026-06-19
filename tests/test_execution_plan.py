"""Execution-plan tests for neutral pipeline topology.

Lattice: RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json

from report_foundry.factory import build_case_rubric, build_execution_plan, build_source_plan, build_visual_plan, write_run_package


def test_execution_plan_turns_source_and_visual_plans_into_pipeline_tasks() -> None:
    rubric = build_case_rubric("current SpaceX IPO launch newsletter", audience="executive readers")
    source_plan = build_source_plan(rubric)
    visual_plan = build_visual_plan(rubric)

    plan = build_execution_plan(topic=rubric.topic, source_plan=source_plan, visual_plan=visual_plan)

    assert plan.workspace_id.startswith("report-foundry-")
    assert plan.workspace_policy == "isolated_run_directory"
    assert plan.notification_policy == "step completion emits compact status plus output pointers"

    research_tasks = [task for task in plan.tasks if task.department == "research"]
    assert len(research_tasks) == len(source_plan.items)
    assert any(task.task_id == "research-starlink-economics" for task in research_tasks)
    assert all(task.work_section.startswith("research/") for task in research_tasks)
    assert all("source_plan.json" in task.inputs for task in research_tasks)
    assert all("required_outputs_present" in task.health_checks for task in research_tasks)

    synthesis = next(task for task in plan.tasks if task.task_id == "synthesis-claims")
    assert {task.task_id for task in research_tasks} <= set(synthesis.depends_on)
    assert synthesis.work_section == "synthesis/claims"

    visual_tasks = [task for task in plan.tasks if task.department == "visuals"]
    assert {task.task_id for task in visual_tasks} >= {"visuals-business-segment-map", "visuals-numbers-chart", "visuals-bull-bear-matrix"}
    assert all("synthesis-claims" in task.depends_on for task in visual_tasks)

    qa = plan.tasks[-1]
    assert qa.task_id == "qa-final-gates"
    assert qa.department == "qa"
    assert "research_gate_result.json" in qa.outputs


def test_write_run_package_persists_execution_plan(tmp_path) -> None:
    out_dir = tmp_path / "run"

    package = write_run_package(topic="current SpaceX IPO launch newsletter", audience="executive readers", out_dir=out_dir)

    assert (out_dir / "execution_plan.json").exists()
    execution_plan = json.loads((out_dir / "execution_plan.json").read_text(encoding="utf-8"))
    assert execution_plan["workspace_id"] == package.execution_plan.workspace_id
    assert any(task["task_id"] == "research-starlink-economics" for task in execution_plan["tasks"])
    assert any(task["task_id"] == "qa-final-gates" for task in execution_plan["tasks"])
