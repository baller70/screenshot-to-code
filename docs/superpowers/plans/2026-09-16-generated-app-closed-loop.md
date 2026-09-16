# Generated App Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic quality evidence, repair-loop packets, ImageGen packet metadata, build history, and backend adapter exports for generated websites.

**Architecture:** Extend the existing `backend/generated_app` control plane with focused modules for visual diffing, repair-loop assembly, and report history. Keep the current WebSocket generation path intact and expose new capabilities through export/audit endpoints and lightweight frontend controls.

**Tech Stack:** FastAPI, Pydantic, BeautifulSoup, Pillow, JSONL storage, React/Vite, existing mirror-mode payloads.

**Spec:** `docs/superpowers/specs/2026-09-16-generated-app-closed-loop-design.md`

## Global Constraints

- Do not add OpenAI API requirements.
- Do not auto-run Codex CLI from a background loop in this slice.
- Preserve fixture-backed export as the default.
- Missing visual evidence should lower confidence, not block export.
- Use focused tests for each backend behavior before implementation.

---

### Task 1: Region Visual Diff Scoring

**Files:**
- Create: `backend/generated_app/visual_diff.py`
- Test: `backend/tests/test_generated_app_visual_diff.py`

**Interfaces:**
- Produces: `compare_visual_regions(reference_data_url: str, candidate_data_url: str, regions: list[RegionSpec] | None = None) -> VisualDiffReport`

- [ ] Write tests for identical images, region mismatch, and default region generation.
- [ ] Implement data URL decoding and Pillow region comparison.
- [ ] Return overall score, per-region score, and repair instructions.
- [ ] Verify with `cd backend && uvx poetry run pytest tests/test_generated_app_visual_diff.py -v`.

### Task 2: Repair Loop Packet

**Files:**
- Create: `backend/generated_app/repair_loop.py`
- Modify: `backend/generated_app/repair.py`
- Modify: `backend/routes/export.py`
- Test: `backend/tests/test_generated_app_repair_loop.py`

**Interfaces:**
- Produces: `build_repair_loop_report(html: str, smoke_report: dict | None = None, visual_report: VisualDiffReport | None = None, attempt: int = 1) -> RepairLoopReport`
- Route: `POST /api/generated-app/repair-loop`

- [ ] Write tests for passing loop and failing visual/smoke loop.
- [ ] Implement loop report model with `shouldRepair`, `nextPrompt`, `score`, and `evidence`.
- [ ] Add endpoint.
- [ ] Verify with focused backend tests.

### Task 3: Build History

**Files:**
- Create: `backend/generated_app/history.py`
- Modify: `backend/routes/export.py`
- Test: `backend/tests/test_generated_app_history.py`

**Interfaces:**
- Produces: `append_build_report(report: BuildReport, store_path: Path | None = None) -> BuildReport`
- Produces: `list_build_reports(limit: int = 25, store_path: Path | None = None) -> list[BuildReport]`
- Routes: `POST /api/generated-app/history`, `GET /api/generated-app/history`

- [ ] Write tests using a temporary JSONL store.
- [ ] Implement append/list.
- [ ] Add routes.
- [ ] Verify with focused backend tests.

### Task 4: Backend Adapter Export

**Files:**
- Modify: `backend/generated_app/exporter.py`
- Modify: `backend/routes/export.py`
- Test: `backend/tests/test_generated_app_export.py`

**Interfaces:**
- Extends: `build_generated_app_export(code: str, app_name: str = "generated-app", backend_adapter: BackendAdapter = "fixture") -> bytes`
- Request field: `backendAdapter`

- [ ] Write tests for `sqlite`, `postgres`, and `webhook` adapter scaffolds.
- [ ] Generate adapter-specific backend files without adding dependencies.
- [ ] Include adapter choice in README and manifest adjunct files.
- [ ] Verify export tests.

### Task 5: Packet Mode UI and Report Actions

**Files:**
- Modify: `frontend/src/components/unified-input/tabs/UploadTab.tsx`
- Modify: `frontend/src/components/preview/PreviewPane.tsx`
- Modify: `frontend/src/components/preview/download.ts`
- Test: `frontend/src/tests/qa.test.ts`

**Interfaces:**
- Packet mode labels and sidecar text are appended to the existing text prompt.
- Adds report action that calls `/api/generated-app/repair-loop`.

- [ ] Add packet metadata controls only for multi-image uploads.
- [ ] Add repair report request helper.
- [ ] Add preview toolbar button for report generation.
- [ ] Verify with `cd frontend && pnpm exec tsc --noEmit` and production build.

### Task 6: Production Verification

**Files:**
- No new source files.

**Interfaces:**
- Production URL remains `https://screenshot-to-code-factory.194-146-12-139.sslip.io`.

- [ ] Run `cd backend && uvx poetry run pytest`.
- [ ] Run `cd backend && uvx poetry run pyright`.
- [ ] Run `cd frontend && pnpm build`.
- [ ] Deploy changed files to Contabo.
- [ ] Verify public health, repair-loop endpoint, history endpoint, and adapter export ZIP.
- [ ] Commit and push.

## Self-Review

- Spec coverage: visual scoring, repair loop, packet UI, history, and adapter export each have a task.
- Placeholder scan: no deferred TBD tasks.
- Type consistency: request fields and function names match the planned route contracts.
