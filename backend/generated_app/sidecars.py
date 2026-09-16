import json
import struct
import zlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SidecarMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str
    raw_text: str = Field(alias="rawText")
    parsed_json: dict[str, Any] | list[Any] | None = Field(
        default=None,
        alias="parsedJson",
    )
    warning: str | None = None


def _parse_sidecar_text(raw_text: str, source: str) -> SidecarMetadata:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return SidecarMetadata(
            source=source,
            rawText=raw_text,
            warning=f"Invalid sidecar JSON: {exc.msg}",
        )

    return SidecarMetadata(
        source=source,
        rawText=raw_text,
        parsedJson=parsed if isinstance(parsed, (dict, list)) else None,
        warning=None if isinstance(parsed, (dict, list)) else "Sidecar JSON was not an object or array.",
    )


def parse_sidecar_texts(raw_sidecars: list[str]) -> list[SidecarMetadata]:
    return [
        _parse_sidecar_text(raw_text.strip(), "request")
        for raw_text in raw_sidecars
        if raw_text.strip()
    ]


def _png_chunks(png_bytes: bytes) -> list[tuple[str, bytes]]:
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return []

    chunks: list[tuple[str, bytes]] = []
    offset = 8
    while offset + 12 <= len(png_bytes):
        length = struct.unpack(">I", png_bytes[offset : offset + 4])[0]
        chunk_type = png_bytes[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(png_bytes):
            break
        chunks.append((chunk_type.decode("latin-1"), png_bytes[data_start:data_end]))
        offset = crc_end
    return chunks


def _decode_text_chunk(chunk_type: str, data: bytes) -> tuple[str, str] | None:
    if chunk_type == "tEXt":
        if b"\x00" not in data:
            return None
        keyword, text = data.split(b"\x00", 1)
        return keyword.decode("latin-1", errors="replace"), text.decode("utf-8", errors="replace")

    if chunk_type == "zTXt":
        parts = data.split(b"\x00", 2)
        if len(parts) != 3:
            return None
        keyword, compression_method, compressed = parts
        if compression_method != b"\x00":
            return None
        try:
            text = zlib.decompress(compressed).decode("utf-8", errors="replace")
        except zlib.error:
            return None
        return keyword.decode("latin-1", errors="replace"), text

    if chunk_type == "iTXt":
        parts = data.split(b"\x00", 5)
        if len(parts) != 6:
            return None
        keyword, compression_flag, compression_method, _language, _translated, text = parts
        if compression_flag == b"\x01":
            if compression_method != b"\x00":
                return None
            try:
                decoded = zlib.decompress(text).decode("utf-8", errors="replace")
            except zlib.error:
                return None
        else:
            decoded = text.decode("utf-8", errors="replace")
        return keyword.decode("latin-1", errors="replace"), decoded

    return None


def extract_png_sidecars(png_bytes: bytes) -> list[SidecarMetadata]:
    sidecars: list[SidecarMetadata] = []
    for chunk_type, data in _png_chunks(png_bytes):
        if chunk_type not in {"tEXt", "zTXt", "iTXt"}:
            continue
        decoded = _decode_text_chunk(chunk_type, data)
        if decoded is None:
            continue
        keyword, text = decoded
        if "sidecar" not in keyword.lower() and "layout" not in keyword.lower():
            continue
        sidecars.append(_parse_sidecar_text(text, f"png:{chunk_type}:{keyword}"))
    return sidecars


def build_sidecar_prompt_block(sidecars: list[SidecarMetadata]) -> str:
    if not sidecars:
        return ""

    blocks = [
        "## ImageGen sidecar metadata",
        "",
        "- Treat this sidecar metadata as authoritative when it names screen IDs, routes, element IDs, bounds, typography, assets, or interactions.",
        "- If a sidecar conflicts with visual guessing, follow the sidecar and preserve its IDs in the generated code.",
    ]
    for index, sidecar in enumerate(sidecars, start=1):
        blocks.append("")
        blocks.append(f"### Sidecar {index} ({sidecar.source})")
        if sidecar.warning:
            blocks.append(f"Warning: {sidecar.warning}")
            blocks.append(sidecar.raw_text)
        else:
            blocks.append(json.dumps(sidecar.parsed_json, indent=2, sort_keys=True))
    return "\n".join(blocks)
