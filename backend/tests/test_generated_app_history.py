from pathlib import Path

from generated_app.history import BuildReport, append_build_report, list_build_reports


def test_append_and_list_build_reports(tmp_path: Path) -> None:
    store = tmp_path / "reports.jsonl"
    first = BuildReport(
        buildId="build-1",
        appName="PulseForge",
        score=72,
        shouldRepair=True,
        summary="Needs repair",
    )
    second = BuildReport(
        buildId="build-2",
        appName="PulseForge",
        score=94,
        shouldRepair=False,
        summary="Ready",
    )

    append_build_report(first, store_path=store)
    append_build_report(second, store_path=store)

    reports = list_build_reports(store_path=store)

    assert [report.build_id for report in reports] == ["build-2", "build-1"]
    assert reports[0].summary == "Ready"


def test_list_build_reports_limits_results(tmp_path: Path) -> None:
    store = tmp_path / "reports.jsonl"
    for index in range(4):
        append_build_report(
            BuildReport(
                buildId=f"build-{index}",
                appName="App",
                score=index,
                shouldRepair=False,
                summary="ok",
            ),
            store_path=store,
        )

    reports = list_build_reports(limit=2, store_path=store)

    assert [report.build_id for report in reports] == ["build-3", "build-2"]
