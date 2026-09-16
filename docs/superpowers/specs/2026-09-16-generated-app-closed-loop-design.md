# Generated App Closed Loop Design

## Goal

Raise the ImageGen 2.5 website-builder baseline by adding evidence-driven mirror quality controls: region visual diff scoring, repair-loop packets, packet-mode upload metadata, build history, and selectable backend export adapters.

## Scope

This slice extends the existing generated-app control plane. It does not replace the WebSocket generation path, does not add OpenAI API usage, and does not make model calls from background jobs.

## Architecture

- `backend/generated_app/visual_diff.py` compares reference and rendered screenshots by stable regions and returns a score, per-region findings, and repair instructions.
- `backend/generated_app/repair_loop.py` combines manifest audit, optional smoke report, optional visual diff report, and prior attempts into a closed-loop repair packet.
- `backend/generated_app/history.py` stores build reports as JSONL so each generated site has a durable quality trail.
- `backend/generated_app/exporter.py` adds backend adapter modes: `fixture`, `sqlite`, `postgres`, and `webhook`.
- `frontend/src/components/unified-input/tabs/UploadTab.tsx` exposes packet mode as a first-class ImageGen 2.5 workflow with per-image role labels and sidecar text.
- `frontend/src/components/preview/PreviewPane.tsx` surfaces a build report action so the user can inspect quality gates without leaving the app.

## Data Flow

1. User uploads 1-5 ImageGen images.
2. Packet mode labels each image as landing, programs, lab, results, booking, or custom intent.
3. The generation payload includes sidecar metadata and mirror-mode controls.
4. Generated HTML can be audited through `/api/generated-app/repair-loop`.
5. Visual diff evidence, smoke failures, and manifest gates are merged into one repair prompt.
6. Exported projects include manifest, quality gates, repair prompt, and the selected backend adapter scaffold.
7. Build history stores score snapshots and report metadata for repeatable factory QA.

## Non-Goals

- No autonomous model repair loop in this slice.
- No production database provisioning.
- No forced backend adapter; fixture remains the default.
- No brittle full-page pixel-perfect threshold as the only pass/fail signal.

## Success Criteria

- Visual diff reports identify weak regions and increase `visualEvidence`.
- Repair-loop endpoint returns a deterministic prompt and `shouldRepair` flag.
- Export ZIP supports fixture, SQLite, Postgres, and webhook backend scaffolds.
- Packet-mode UI lets users label each source screenshot and add sidecar metadata.
- Build report endpoint stores and lists generated quality reports.
- Tests cover each new backend behavior.
