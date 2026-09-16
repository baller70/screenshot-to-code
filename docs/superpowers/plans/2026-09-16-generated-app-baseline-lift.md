# Generated App Baseline Lift Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add generated-app analysis, scoring, sidecar ingestion, fixture-backed backend export, and smoke-test evidence for ImageGen 2.5 mirror-mode websites.

**Architecture:** Add a backend control-plane layer that derives a `GeneratedAppManifest` from generated HTML and optional sidecars. Reuse that manifest for score reports, project export, and future repair loops without changing the core WebSocket generation path.

**Tech Stack:** FastAPI, Pydantic, BeautifulSoup, Python standard library ZIP/PNG parsing, existing frontend React/Vite, existing Puppeteer stress tooling.

**Spec:** `docs/superpowers/specs/2026-09-16-generated-app-baseline-lift-design.md`

## Global Constraints

- Use Codex CLI for LLM generation; do not add OpenAI API requirements for this path.
- Preserve generated reference/stress artifacts under ignored `stress-tests/` folders.
- Backend tests must pass after code changes.
- Pyright must report no new changed-file errors.
- Generated backend export starts fixture-backed; it does not need a production database server in this phase.
- Missing evidence is a warning or failed gate, not a pass.

---

### Task 1: Generated App Manifest Analyzer

**Files:**
- Create: `backend/generated_app/__init__.py`
- Create: `backend/generated_app/manifest.py`
- Test: `backend/tests/test_generated_app_manifest.py`

**Interfaces:**
- Produces: `analyze_generated_app_html(html: str) -> GeneratedAppManifest`
- Produces: `GeneratedAppManifest.model_dump()` with `routes`, `assets`, `mirrorIds`, `backendContracts`, `interactions`, `warnings`, and `scores`.

- [ ] **Step 1: Write failing tests**

```python
def test_extracts_literal_route_and_asset_registries() -> None:
    html = """
    <script>
    const MIRROR_ROUTE_REGISTRY=[
      {inputIndex:0,route:'#home',label:'Home',viewportRole:'landing',sourceIntent:'conversion',majorRegions:['nav','hero']}
    ];
    const MIRROR_ASSET_REGISTRY=[
      {assetId:'hero',sourceInputIndexes:[0],role:'hero-photo',reusePolicy:'home',renderStrategy:'local-crop'}
    ];
    </script>
    <section id="home" class="page active" data-mirror-id="home-page">
      <form data-api-route="/api/evaluations"><input name="athleteName"><button>Reserve Evaluation</button></form>
    </section>
    """
    manifest = analyze_generated_app_html(html)
    assert manifest.routes[0].route == "#home"
    assert manifest.assets[0].asset_id == "hero"
    assert "home-page" in manifest.mirror_ids
    assert manifest.backend_contracts[0].api_route == "/api/evaluations"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_manifest.py -v`
Expected: FAIL because `generated_app.manifest` does not exist.

- [ ] **Step 3: Implement analyzer**

Create Pydantic models and parser helpers. Parse JavaScript literal registries with a conservative regex and key quoting fallback. Use BeautifulSoup for DOM inference.

- [ ] **Step 4: Verify task**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_manifest.py -v`
Expected: PASS.

### Task 2: Baseline Score Calculator

**Files:**
- Modify: `backend/generated_app/manifest.py`
- Test: `backend/tests/test_generated_app_manifest.py`

**Interfaces:**
- Produces: `GeneratedAppScores(overall: int, routeCompleteness: int, registryCompleteness: int, mirrorIdCoverage: int, assetReuse: int, backendContractCoverage: int, interactionReadiness: int, visualEvidence: int)`

- [ ] **Step 1: Write failing score tests**

Add tests for complete HTML scoring high and missing registries scoring lower with warnings.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_manifest.py -v`
Expected: FAIL on missing score fields.

- [ ] **Step 3: Implement scoring**

Calculate component scores from manifest evidence and warnings. Clamp `overall` to `0..100`.

- [ ] **Step 4: Verify task**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_manifest.py -v`
Expected: PASS.

### Task 3: Generated App Export Package

**Files:**
- Create: `backend/generated_app/exporter.py`
- Modify: `backend/routes/export.py`
- Test: `backend/tests/test_generated_app_export.py`

**Interfaces:**
- Produces: `build_generated_app_export(code: str, app_name: str = "generated-app") -> bytes`
- Route: `POST /api/export/generated-app` with `{ "code": "...", "appName": "pulseforge" }`

- [ ] **Step 1: Write failing export tests**

Assert the ZIP contains `frontend/index.html`, `backend/main.py`, `backend/fixtures.json`, `backend/schema.sql`, `backend/tests/test_smoke.py`, `manifest.json`, and `README.md`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_export.py -v`
Expected: FAIL because exporter does not exist.

- [ ] **Step 3: Implement exporter**

Generate a fixture-backed FastAPI app with endpoints for detected backend contracts and a static README explaining how to run it.

- [ ] **Step 4: Verify task**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_export.py -v`
Expected: PASS.

### Task 4: Sidecar Ingestion

**Files:**
- Create: `backend/generated_app/sidecars.py`
- Modify: `backend/prompts/create/image.py`
- Modify: `backend/prompts/request_parsing.py`
- Test: `backend/tests/test_generated_app_sidecars.py`
- Test: `backend/tests/test_prompts.py`

**Interfaces:**
- Produces: `extract_png_sidecars(png_bytes: bytes) -> list[SidecarMetadata]`
- Produces: `build_sidecar_prompt_block(sidecars: list[SidecarMetadata]) -> str`

- [ ] **Step 1: Write failing sidecar tests**

Cover JSON sidecar text and PNG `tEXt`/`iTXt` chunk extraction.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_sidecars.py tests/test_prompts.py -v`
Expected: FAIL because sidecar helpers do not exist.

- [ ] **Step 3: Implement sidecar parser and prompt block**

Use Python `struct`/`zlib` for PNG chunks. Invalid JSON is preserved as raw text with a warning.

- [ ] **Step 4: Verify task**

Run: `cd backend && uvx poetry run pytest tests/test_generated_app_sidecars.py tests/test_prompts.py -v`
Expected: PASS.

### Task 5: Interaction Smoke Evidence

**Files:**
- Modify: `stress-tests/capture_html_routes.mjs`
- Create: `stress-tests/smoke_generated_app.mjs`

**Interfaces:**
- Produces: JSON report with route activation, form fill/submit checks, horizontal overflow checks, and mirror-node counts.

- [ ] **Step 1: Add smoke script syntax and fixture checks**

Create script that opens generated HTML, uses route registry when present, fills forms with deterministic sample values, clicks submit buttons, and records failures.

- [ ] **Step 2: Verify script syntax**

Run: `cd frontend && pnpm exec node --check ../stress-tests/smoke_generated_app.mjs`
Expected: PASS.

### Task 6: Production Verification and Save

**Files:**
- No new production files unless prior tasks require route registration in `backend/main.py`.

**Interfaces:**
- Production app remains at `https://screenshot-to-code-factory.194-146-12-139.sslip.io`.

- [ ] **Step 1: Run full backend tests**

Run: `cd backend && uvx poetry run pytest`
Expected: PASS.

- [ ] **Step 2: Run pyright**

Run: `cd backend && uvx poetry run pyright`
Expected: `0 errors`; no new changed-file warnings.

- [ ] **Step 3: Run frontend tests/build if stress scripts or UI changed**

Run: `cd frontend && pnpm test --runInBand && pnpm build`
Expected: PASS.

- [ ] **Step 4: Deploy backend changes to Contabo**

Copy changed backend files to `/opt/apps/screenshot-to-code-factory`, restart `screenshot-to-code-factory-backend`, and verify `/api/design-systems` returns `HTTP/2 200`.

- [ ] **Step 5: Run packet evidence**

Use `stress-tests/run_imagegen_packet_ws.py` and `stress-tests/smoke_generated_app.mjs` on a generated PulseForge packet.

- [ ] **Step 6: Commit and push**

Commit coherent changes and push to `baller70/codex/imagegen-packet-fidelity-mode`.

## Self-Review

- Spec coverage: all seven requested baseline lifts are represented as backend builder/exporter, visual evidence, sidecar ingestion, smoke tests, registry enforcement, and scoring.
- Placeholder scan: no TBD/TODO placeholders are required for task execution.
- Type consistency: manifest/export/sidecar function names are consistent across tasks.
