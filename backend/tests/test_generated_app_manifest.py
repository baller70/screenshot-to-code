import json

from generated_app.manifest import analyze_generated_app_html


def test_extracts_literal_route_and_asset_registries() -> None:
    html = """
    <!doctype html>
    <html>
      <head>
        <script>
          const MIRROR_ROUTE_REGISTRY=[
            {inputIndex:0,route:'#home',label:'Home',viewportRole:'landing',sourceIntent:'conversion',majorRegions:['nav','hero']},
            {inputIndex:1,route:'#book',label:'Book Eval',viewportRole:'booking',sourceIntent:'reserve evaluation',majorRegions:['form','summary']}
          ];
          const MIRROR_ASSET_REGISTRY=[
            {assetId:'hero',sourceInputIndexes:[0],role:'hero-photo',reusePolicy:'home',renderStrategy:'local-crop'}
          ];
        </script>
      </head>
      <body>
        <section id="home" class="page active" data-mirror-id="home-page">
          <a href="#book" data-mirror-id="home-book-cta">Book Eval</a>
        </section>
        <section id="book" class="page" data-mirror-id="book-page">
          <form data-api-route="/api/evaluations" data-mirror-id="eval-form">
            <input name="athleteName">
            <button type="submit">Reserve Evaluation</button>
          </form>
        </section>
      </body>
    </html>
    """

    manifest = analyze_generated_app_html(html)

    assert [route.route for route in manifest.routes] == ["#home", "#book"]
    assert manifest.routes[0].input_index == 0
    assert manifest.routes[1].major_regions == ["form", "summary"]
    assert manifest.assets[0].asset_id == "hero"
    assert manifest.assets[0].source_input_indexes == [0]
    assert "home-page" in manifest.mirror_ids
    assert "eval-form" in manifest.mirror_ids
    assert manifest.backend_contracts[0].api_route == "/api/evaluations"
    assert manifest.backend_contracts[0].method == "POST"
    assert manifest.interactions[0].kind == "link"
    assert manifest.scores.route_completeness == 20
    assert manifest.scores.registry_completeness == 20


def test_falls_back_to_dom_routes_and_warns_when_registries_are_missing() -> None:
    html = """
    <main>
      <nav><a href="#home">Home</a><a href="#programs">Programs</a></nav>
      <section id="home" data-mirror-id="home-page"><button>Start</button></section>
      <section id="programs"><img src="data:image/png;base64,abc"></section>
    </main>
    """

    manifest = analyze_generated_app_html(html)

    assert [route.route for route in manifest.routes] == ["#home", "#programs"]
    assert manifest.assets[0].role == "image"
    assert "Missing MIRROR_ROUTE_REGISTRY; inferred routes from DOM links." in manifest.warnings
    assert "Missing MIRROR_ASSET_REGISTRY; inferred assets from DOM media." in manifest.warnings
    assert manifest.scores.registry_completeness < 20


def test_manifest_dump_uses_api_friendly_aliases() -> None:
    manifest = analyze_generated_app_html(
        """
        <script>
          const MIRROR_ROUTE_REGISTRY=[{inputIndex:0,route:'#home',label:'Home',viewportRole:'landing',sourceIntent:'conversion',majorRegions:['hero']}];
          const MIRROR_ASSET_REGISTRY=[{assetId:'logo',sourceInputIndexes:[0],role:'logo',reusePolicy:'global',renderStrategy:'text'}];
        </script>
        <section id="home" data-mirror-id="home-page"></section>
        """
    )

    payload = manifest.model_dump(by_alias=True)

    assert payload["mirrorIds"] == ["home-page"]
    assert payload["routes"][0]["inputIndex"] == 0
    assert payload["assets"][0]["assetId"] == "logo"
    json.dumps(payload)
