from generated_app.repair_loop import build_repair_loop_report
from generated_app.visual_diff import RegionResult, VisualDiffReport


HTML = """
<script>
  const MIRROR_ROUTE_REGISTRY=[
    {inputIndex:0,route:'#home',label:'Home',viewportRole:'landing',sourceIntent:'lead',majorRegions:['hero']}
  ];
  const MIRROR_ASSET_REGISTRY=[
    {assetId:'logo',sourceInputIndexes:[0],role:'logo',reusePolicy:'global',renderStrategy:'text'}
  ];
</script>
<section id="home" data-mirror-id="home-page">
  <a href="#home">Home</a>
  <form data-api-route="/api/leads">
    <input name="email">
    <button type="submit">Join</button>
  </form>
</section>
"""


def test_repair_loop_passes_when_gates_and_visuals_are_good() -> None:
    report = build_repair_loop_report(HTML)

    assert report.should_repair is False
    assert report.score >= 80
    assert report.next_prompt.startswith("# Generated App Mirror Repair Packet")


def test_repair_loop_fails_when_smoke_or_visual_evidence_fails() -> None:
    visual_report = VisualDiffReport(
        overallScore=45,
        regions=[
            RegionResult(
                regionId="hero",
                label="Hero",
                score=45,
                meanDelta=140,
                repairInstruction="Rebuild Hero.",
            )
        ],
        repairInstructions=["Rebuild Hero."],
    )

    report = build_repair_loop_report(
        HTML,
        smoke_report={"failures": ["Route failed smoke check: #home"]},
        visual_report=visual_report,
        attempt=2,
    )

    assert report.should_repair is True
    assert report.attempt == 2
    assert report.visual_report is visual_report
    assert "Route failed smoke check: #home" in report.next_prompt
    assert "Rebuild Hero." in report.next_prompt
