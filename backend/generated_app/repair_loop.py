# pyright: reportUnknownVariableType=false
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from generated_app.repair import audit_generated_app_html
from generated_app.visual_diff import VisualDiffReport


class RepairLoopReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attempt: int
    score: int
    should_repair: bool = Field(alias="shouldRepair")
    next_prompt: str = Field(alias="nextPrompt")
    evidence: list[str]
    audit: dict[str, Any]
    visual_report: VisualDiffReport | None = Field(default=None, alias="visualReport")


def _visual_evidence(visual_report: VisualDiffReport | None) -> list[str]:
    if not visual_report:
        return []
    evidence = [f"Visual score: {visual_report.overall_score}"]
    evidence.extend(visual_report.repair_instructions)
    return evidence


def _combined_score(audit_score: int, visual_report: VisualDiffReport | None) -> int:
    if not visual_report:
        return audit_score
    return round((audit_score * 0.65) + (visual_report.overall_score * 0.35))


def build_repair_loop_report(
    html: str,
    smoke_report: dict[str, Any] | None = None,
    visual_report: VisualDiffReport | None = None,
    attempt: int = 1,
) -> RepairLoopReport:
    audit = audit_generated_app_html(html, smoke_report)
    failed_gates = [gate for gate in audit.gates if not gate.ok and gate.severity == "error"]
    visual_failed = visual_report is not None and visual_report.overall_score < 85
    score = _combined_score(audit.manifest.scores.overall, visual_report)
    visual_lines = _visual_evidence(visual_report)
    prompt_parts = [
        audit.repair_prompt,
        "",
        "## Closed Loop Attempt",
        f"- Attempt: {attempt}",
        f"- Combined score: {score}",
    ]
    if visual_lines:
        prompt_parts.extend(["", "## Visual Evidence", *[f"- {line}" for line in visual_lines]])

    return RepairLoopReport(
        attempt=attempt,
        score=score,
        shouldRepair=bool(failed_gates or visual_failed),
        nextPrompt="\n".join(prompt_parts),
        evidence=[
            f"Audit score: {audit.manifest.scores.overall}",
            *[f"Failed gate: {gate.label}" for gate in failed_gates],
            *visual_lines,
        ],
        audit=audit.model_dump(by_alias=True),
        visualReport=visual_report,
    )
