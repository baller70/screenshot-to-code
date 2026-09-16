#!/usr/bin/env python3
"""Run a multi-image ImageGen packet through the live websocket generator."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import time
from pathlib import Path
from typing import Any

import websockets


DEFAULT_MIRROR_MODE = {
    "enabled": True,
    "packetMode": True,
    "sidecarMode": True,
    "assetRegistry": True,
    "routeRegistry": True,
    "backendContract": True,
    "visualRepair": True,
    "targetFidelity": "pixel",
}


def image_to_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def event_preview(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("value")
    compact = {k: v for k, v in event.items() if k != "value"}
    if isinstance(value, str):
        compact["valuePreview"] = value[:300]
        compact["valueLength"] = len(value)
    elif value is not None:
        compact["value"] = value
    return compact


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generationType": "create",
        "inputMode": "image",
        "generatedCodeConfig": args.stack,
        "openAiApiKey": None,
        "openAiBaseURL": None,
        "replicateApiKey": None,
        "screenshotOneApiKey": None,
        "anthropicApiKey": None,
        "geminiApiKey": None,
        "isImageGenerationEnabled": True,
        "isAssetExtractionEnabled": True,
        "editorTheme": "espresso",
        "codeGenerationModel": "codex-cli",
        "selectedDesignSystemId": None,
        "isTermOfServiceAccepted": True,
        "designSystem": None,
        "mirrorMode": DEFAULT_MIRROR_MODE,
        "prompt": {
            "text": args.prompt,
            "images": [image_to_data_url(path) for path in args.images],
            "videos": [],
        },
        "history": [],
    }


async def run(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(args)
    payload_path = args.output_dir / f"{args.name}-payload.json"
    payload_for_disk = dict(payload)
    payload_for_disk["prompt"] = dict(payload["prompt"])
    payload_for_disk["prompt"]["images"] = [
        {"path": str(path), "bytes": path.stat().st_size} for path in args.images
    ]
    payload_path.write_text(json.dumps(payload_for_disk, indent=2), encoding="utf-8")

    started = time.monotonic()
    events: list[dict[str, Any]] = []
    full_events: list[dict[str, Any]] = []
    option_codes: dict[int, str] = {}
    chunks: dict[int, list[str]] = {}
    close: dict[str, Any] = {}

    async with websockets.connect(args.websocket_url, max_size=None) as ws:
        await ws.send(json.dumps(payload))
        while True:
            try:
                raw = await ws.recv()
            except websockets.ConnectionClosed as exc:
                close = {"code": exc.code, "reason": exc.reason}
                break

            event = json.loads(raw)
            full_events.append(event)
            events.append(event_preview(event))
            variant_index = int(event.get("variantIndex", 0))
            event_type = event.get("type")
            value = event.get("value")
            if event_type == "chunk" and isinstance(value, str):
                chunks.setdefault(variant_index, []).append(value)
            if event_type == "setCode" and isinstance(value, str):
                option_codes[variant_index] = value

    duration = time.monotonic() - started
    if not option_codes:
        for variant_index, pieces in chunks.items():
            joined = "".join(pieces).strip()
            if joined:
                option_codes[variant_index] = joined

    selected_index = min(option_codes) if option_codes else None
    selected_code = option_codes[selected_index] if selected_index is not None else ""
    html_path = args.output_dir / f"{args.name}.html"
    if selected_code:
        html_path.write_text(selected_code, encoding="utf-8")

    events_path = args.output_dir / f"{args.name}-events.json"
    full_events_path = args.output_dir / f"{args.name}-events-full.json"
    report_path = args.output_dir / f"{args.name}-report.json"
    events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
    full_events_path.write_text(json.dumps(full_events, indent=2), encoding="utf-8")

    errors = [
        event
        for event in events
        if event.get("type") in {"error", "variantError"}
    ]
    report = {
        "websocketUrl": args.websocket_url,
        "durationSeconds": round(duration, 2),
        "eventCount": len(events),
        "close": close,
        "selectedVariant": selected_index,
        "codeLength": len(selected_code),
        "htmlPath": str(html_path) if selected_code else None,
        "eventsPath": str(events_path),
        "fullEventsPath": str(full_events_path),
        "payloadPath": str(payload_path),
        "variantCodeLengths": {
            str(index): len(code) for index, code in sorted(option_codes.items())
        },
        "hasRouteRegistry": "MIRROR_ROUTE_REGISTRY" in selected_code,
        "hasAssetRegistry": "MIRROR_ASSET_REGISTRY" in selected_code,
        "hasMirrorIds": "data-mirror-id" in selected_code,
        "errors": errors,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if selected_code and close.get("code") == 1000 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--websocket-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="generated-imagegen-packet")
    parser.add_argument("--stack", default="html_tailwind")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image", dest="images", type=Path, action="append", required=True)
    return parser.parse_args()


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
