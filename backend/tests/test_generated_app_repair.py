from generated_app.repair import audit_generated_app_html


def test_audit_builds_quality_gates_and_repair_prompt() -> None:
    audit = audit_generated_app_html(
        """
        <main>
          <a href="#home">Home</a>
          <section id="home"><button>Start</button></section>
        </main>
        """,
        smoke_report={"failures": ["Route failed smoke check: #home"]},
    )

    gates = {gate.gate_id: gate for gate in audit.gates}

    assert gates["route-registry"].ok is False
    assert gates["smoke-report"].ok is False
    assert "MIRROR_ROUTE_REGISTRY" in gates["route-registry"].repair_instruction
    assert "Route failed smoke check: #home" in audit.repair_prompt
    assert "Return the complete updated HTML" in audit.repair_prompt


def test_audit_passes_core_gates_for_structured_generated_app() -> None:
    audit = audit_generated_app_html(
        """
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
    )

    gates = {gate.gate_id: gate for gate in audit.gates}

    assert gates["route-registry"].ok is True
    assert gates["asset-registry"].ok is True
    assert gates["mirror-id-coverage"].ok is True
    assert gates["backend-contracts"].ok is True
    assert gates["interaction-contracts"].ok is True
