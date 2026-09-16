import json
import struct
import zlib

from generated_app.sidecars import (
    build_sidecar_prompt_block,
    extract_png_sidecars,
    parse_sidecar_texts,
)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def make_png_with_text(keyword: str, text: str) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = png_chunk(
        b"IHDR",
        struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0),
    )
    text_chunk = png_chunk(b"tEXt", keyword.encode("latin-1") + b"\x00" + text.encode("utf-8"))
    iend = png_chunk(b"IEND", b"")
    return signature + ihdr + text_chunk + iend


def test_parse_sidecar_texts_keeps_structured_json() -> None:
    sidecars = parse_sidecar_texts([
        json.dumps({"screenId": "home", "bounds": {"x": 0, "y": 0}}),
    ])

    assert sidecars[0].source == "request"
    assert sidecars[0].parsed_json == {"screenId": "home", "bounds": {"x": 0, "y": 0}}
    assert sidecars[0].warning is None


def test_parse_sidecar_texts_preserves_invalid_json_with_warning() -> None:
    sidecars = parse_sidecar_texts(["{not-json"])

    assert sidecars[0].raw_text == "{not-json"
    assert sidecars[0].parsed_json is None
    assert "Invalid sidecar JSON" in (sidecars[0].warning or "")


def test_extract_png_sidecars_reads_text_chunks() -> None:
    png = make_png_with_text("ImageGenSidecar", '{"screenId":"book"}')

    sidecars = extract_png_sidecars(png)

    assert sidecars[0].source == "png:tEXt:ImageGenSidecar"
    assert sidecars[0].parsed_json == {"screenId": "book"}


def test_build_sidecar_prompt_block_marks_metadata_authoritative() -> None:
    sidecars = parse_sidecar_texts(['{"screenId":"home","route":"#home"}'])

    block = build_sidecar_prompt_block(sidecars)

    assert "## ImageGen sidecar metadata" in block
    assert "authoritative" in block
    assert '"screenId": "home"' in block
