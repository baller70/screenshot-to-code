import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_HISTORY_PATH = Path("generated_app_build_reports.jsonl")


class BuildReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    build_id: str = Field(default_factory=lambda: str(uuid4()), alias="buildId")
    app_name: str = Field(alias="appName")
    score: int
    should_repair: bool = Field(alias="shouldRepair")
    summary: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        alias="createdAt",
    )
    report: dict[str, Any] | None = None


def append_build_report(
    report: BuildReport,
    store_path: Path | None = None,
) -> BuildReport:
    path = store_path or DEFAULT_HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(report.model_dump(by_alias=True)) + "\n")
    return report


def list_build_reports(
    limit: int = 25,
    store_path: Path | None = None,
) -> list[BuildReport]:
    path = store_path or DEFAULT_HISTORY_PATH
    if not path.exists():
        return []
    reports: list[BuildReport] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            reports.append(BuildReport.model_validate_json(line))
    return list(reversed(reports))[:limit]
