# Generated App Baseline Lift Design

## Goal

Move Screenshot-to-Code Factory from "image packet to mirrored website" toward "image packet to working app package" by adding generated-app contracts, exportable backend scaffolds, visual verification evidence, sidecar ingestion hooks, registry enforcement, interaction smoke checks, and baseline scoring.

## Scope

This design covers the next production baseline for ImageGen 2.5 mirror mode:

- Analyze generated HTML for route, asset, mirror, backend, and interaction contracts.
- Export a generated app package with frontend HTML, backend scaffold, fixtures, database schema, smoke tests, and README.
- Accept sidecar metadata alongside screenshots and include it in prompt contracts.
- Score generated output for route completeness, registry completeness, mirror IDs, asset reuse, backend contract coverage, and interaction readiness.
- Provide deterministic smoke-test evidence for generated routes and forms.

It does not attempt to make every generated app business-domain-complete on the first pass. The backend scaffold must be real and runnable, but generated business logic starts as deterministic fixture-backed endpoints named from the generated contract.

## Architecture

Add a backend-only control-plane layer first. It analyzes HTML and optional ImageGen sidecar metadata into a `GeneratedAppManifest`, then reuses that manifest for scoring and package export. The existing generation path remains unchanged except for passing sidecar text into prompts and asking Codex to emit stronger contract markers.

Frontend changes can come after the backend control plane is stable. The first UI surface should show the generated app score, detected routes/assets/backend endpoints, and export buttons.

## Core Concepts

### Generated App Manifest

The manifest is the canonical post-generation contract. It is derived from generated HTML plus optional sidecars.

Required fields:

- `routes`: route hash/path, label, source input index, active DOM target, and major regions.
- `assets`: stable asset ID, role, source input indexes, reuse policy, render strategy, and occurrences.
- `mirrorIds`: all `data-mirror-id` values and counts.
- `backendContracts`: forms, buttons, tables, filters, dashboards, booking flows, and generated API/action names.
- `interactions`: nav links, buttons, forms, filters, tabs, accordions, and expected smoke actions.
- `scores`: component scores and overall baseline score.
- `warnings`: actionable issues that keep the mirror from being a true working app.

### Backend Builder

The backend builder exports a runnable fixture-backed FastAPI app:

- `backend/main.py`
- `backend/fixtures.json`
- `backend/schema.sql`
- `backend/tests/test_smoke.py`
- `README.md`

For every detected form or action, it creates a stable endpoint. If details are unknown, it creates deterministic fixture behavior and names the API route from the visible/generated contract.

### Visual Diff Repair Loop

The first implementation should score and capture evidence, not silently mutate code. Repair will be a follow-up mode that feeds score evidence back into Codex as an update request. The system must separate "measurement" from "repair" so failures are explainable.

### Sidecar Ingestion

Sidecars may arrive as:

- text/JSON files uploaded beside screenshots,
- JSON embedded in PNG `iTXt`, `tEXt`, or `zTXt` chunks,
- user-pasted sidecar text.

The first implementation extracts and forwards sidecar JSON/text into the prompt. Authority remains with sidecar metadata when it includes IDs, bounds, typography, routes, assets, or interactions.

### Interaction Smoke Tests

Smoke tests must be deterministic and local:

- route navigation activates the expected page,
- forms can be filled and submitted,
- generated API/action contracts exist in the export package,
- no horizontal overflow at the target viewport,
- all route registry entries have a renderable target.

### Baseline Scoring

The baseline score is a weighted report:

- route completeness: 20
- registry completeness: 20
- mirror ID coverage: 15
- asset registry/reuse: 15
- backend contract coverage: 15
- interaction readiness: 10
- visual evidence availability: 5

Scores must be explicit. Missing evidence is a failed/missing gate, not a pass.

## Error Handling

- Missing route registry: infer routes from nav links and sections, but warn.
- Missing asset registry: infer assets from media and CSS URLs, but warn.
- Missing backend contract: infer forms/buttons as contracts, but warn.
- Invalid sidecar JSON: preserve raw sidecar text and warn instead of dropping it.
- Unrenderable route: include it in smoke failures.

## Testing

Use TDD for each production change.

Required tests:

- Manifest extraction from HTML with literal registries.
- Fallback extraction when registries are absent.
- Backend contract extraction from forms and action buttons.
- Score calculation with pass/fail components.
- Export package contains frontend, backend, fixtures, schema, smoke tests, and README.
- Sidecar extraction from standalone JSON/text and PNG metadata chunks.
- Prompt block includes sidecar authority when sidecars are present.

## Deployment

Deploy backend changes to Contabo via the existing PM2-backed app path. Preserve the app-local `CODEX_HOME` behavior. Verify production health and run at least one local or production packet audit before claiming completion.
