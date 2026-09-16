import json
from io import BytesIO
from zipfile import ZipFile

from generated_app.exporter import build_generated_app_export


HTML = """
<!doctype html>
<html>
  <head>
    <script>
      const MIRROR_ROUTE_REGISTRY=[
        {inputIndex:0,route:'#home',label:'Home',viewportRole:'landing',sourceIntent:'conversion',majorRegions:['hero']},
        {inputIndex:1,route:'#book',label:'Book Eval',viewportRole:'booking',sourceIntent:'reserve evaluation',majorRegions:['form']}
      ];
      const MIRROR_ASSET_REGISTRY=[
        {assetId:'logo',sourceInputIndexes:[0,1],role:'logo',reusePolicy:'global',renderStrategy:'text'}
      ];
    </script>
  </head>
  <body>
    <section id="home" data-mirror-id="home-page"><a href="#book">Book Eval</a></section>
    <section id="book" data-mirror-id="book-page">
      <form id="evaluation" data-api-route="/api/evaluations">
        <input name="athleteName">
        <input name="email">
        <button type="submit">Reserve Evaluation</button>
      </form>
    </section>
  </body>
</html>
"""


def read_zip(export_bytes: bytes) -> dict[str, str]:
    with ZipFile(BytesIO(export_bytes)) as archive:
        return {
            name: archive.read(name).decode("utf-8")
            for name in archive.namelist()
        }


def test_build_generated_app_export_contains_runnable_project_files() -> None:
    files = read_zip(build_generated_app_export(HTML, app_name="Pulse Forge"))

    assert set(files) >= {
        "pulse-forge/frontend/index.html",
        "pulse-forge/backend/main.py",
        "pulse-forge/backend/fixtures.json",
        "pulse-forge/backend/schema.sql",
        "pulse-forge/backend/tests/test_smoke.py",
        "pulse-forge/manifest.json",
        "pulse-forge/quality-gates.json",
        "pulse-forge/repair-prompt.md",
        "pulse-forge/README.md",
    }
    assert "Book Eval" in files["pulse-forge/frontend/index.html"]
    assert "FastAPI" in files["pulse-forge/backend/main.py"]
    assert "@app.post('/api/evaluations')" in files["pulse-forge/backend/main.py"]
    assert "CREATE TABLE IF NOT EXISTS evaluation" in files["pulse-forge/backend/schema.sql"]
    assert "Generated App Mirror Repair Packet" in files["pulse-forge/repair-prompt.md"]
    assert "pytest" in files["pulse-forge/README.md"]


def test_build_generated_app_export_writes_manifest_and_fixtures() -> None:
    files = read_zip(build_generated_app_export(HTML, app_name="Pulse Forge"))

    manifest = json.loads(files["pulse-forge/manifest.json"])
    gates = json.loads(files["pulse-forge/quality-gates.json"])
    fixtures = json.loads(files["pulse-forge/backend/fixtures.json"])

    assert manifest["routes"][1]["route"] == "#book"
    assert manifest["backendContracts"][0]["apiRoute"] == "/api/evaluations"
    assert gates[0]["gateId"] == "route-registry"
    assert fixtures["routes"][0]["route"] == "#home"
    assert fixtures["submissions"] == []


def test_build_generated_app_export_can_generate_sqlite_backend_adapter() -> None:
    files = read_zip(
        build_generated_app_export(
            HTML,
            app_name="Pulse Forge",
            backend_adapter="sqlite",
        )
    )

    assert "sqlite3" in files["pulse-forge/backend/main.py"]
    assert "generated_app.db" in files["pulse-forge/backend/main.py"]
    assert "Backend adapter: sqlite" in files["pulse-forge/README.md"]


def test_build_generated_app_export_can_generate_postgres_backend_adapter() -> None:
    files = read_zip(
        build_generated_app_export(
            HTML,
            app_name="Pulse Forge",
            backend_adapter="postgres",
        )
    )

    assert "DATABASE_URL" in files["pulse-forge/backend/main.py"]
    assert "Postgres adapter placeholder" in files["pulse-forge/backend/main.py"]
    assert "Backend adapter: postgres" in files["pulse-forge/README.md"]


def test_build_generated_app_export_can_generate_webhook_backend_adapter() -> None:
    files = read_zip(
        build_generated_app_export(
            HTML,
            app_name="Pulse Forge",
            backend_adapter="webhook",
        )
    )

    assert "WEBHOOK_URL" in files["pulse-forge/backend/main.py"]
    assert "httpx.post" in files["pulse-forge/backend/main.py"]
    assert "Backend adapter: webhook" in files["pulse-forge/README.md"]
