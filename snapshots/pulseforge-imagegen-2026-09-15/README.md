# PulseForge ImageGen Snapshot

This snapshot preserves the first strong five-screen ImageGen-to-website result before further iteration.

- Date: 2026-09-15
- App branch: `codex/codex-cli-provider`
- Live app: `https://screenshot-to-code-factory.194-146-12-139.sslip.io`
- Input set: five ImageGen-style desktop page references
- Output: one runnable HTML website with Home, Programs, Performance Lab, Results, and Book Eval pages

## Files

- `reference/` contains the five input reference screenshots.
- `output/index.html` is the generated runnable website.
- `output/current-*.png` are Playwright renders of the generated website pages.
- `output/render-report.json` records the page map and render metadata from verification.

## Verification From Original Run

- Production WebSocket generation completed.
- Output HTML length was about 789 KB.
- The generated site embedded 13 image assets as data URLs.
- Rendered pages: `home`, `programs`, `lab`, `results`, `eval`.
