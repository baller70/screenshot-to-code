import asyncio
import base64
import binascii
import mimetypes
import re
import shutil
from urllib.parse import unquote
import uuid
from pathlib import Path
from typing import Any, Optional, cast

from openai.types.chat import ChatCompletionMessageParam

from agent.providers.base import (
    EventSink,
    ExecutedToolCall,
    ProviderTurn,
    StreamEvent,
)


DATA_IMAGE_RE = re.compile(r"^data:image/([a-zA-Z0-9.+-]+);base64,(.*)$", re.DOTALL)
LOCAL_ASSET_RE = re.compile(
    r"(?P<prefix>(?:src|href)=['\"]|url\(['\"]?)"
    r"(?P<path>(?!data:|https?:|//|#)[^'\"\)]+\.(?:png|jpe?g|webp|gif|svg))"
    r"(?P<suffix>['\"]|\)?['\"]?\))",
    re.IGNORECASE,
)
LOCAL_ASSET_STRING_RE = re.compile(
    r"(?P<quote>['\"])"
    r"(?P<path>(?!data:|https?:|//|#)[^'\"\)]+\.(?:png|jpe?g|webp|gif|svg))"
    r"(?P=quote)",
    re.IGNORECASE,
)


def is_codex_cli_available(codex_path: str = "codex") -> bool:
    return shutil.which(codex_path) is not None or Path(codex_path).exists()


def _safe_image_extension(image_type: str) -> str:
    normalized = image_type.lower().replace("jpeg", "jpg")
    if normalized in {"png", "jpg", "webp", "gif"}:
        return normalized
    return "png"


def _write_data_url_image(data_url: str, workdir: Path, index: int) -> Path | None:
    match = DATA_IMAGE_RE.match(data_url)
    if not match:
        return None

    image_type, payload = match.groups()
    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None

    image_path = workdir / f"input-{index}.{_safe_image_extension(image_type)}"
    image_path.write_bytes(image_bytes)
    return image_path


def prepare_codex_prompt_and_images(
    prompt_messages: list[ChatCompletionMessageParam],
    workdir: Path,
) -> tuple[str, list[Path]]:
    image_paths: list[Path] = []
    prompt_sections: list[str] = [
        """You are running as the Codex CLI provider inside Screenshot-to-Code Factory.

Return the completed page as a single full HTML document in a <file path="index.html">...</file> block.
Do not return a partial snippet. Do not use the reference screenshot as a background image.
Create local asset files from attached screenshots when cropped logos, photos, icons, or textures improve fidelity.
Reference those generated local assets with relative paths; the provider will inline them for the preview.
Prefer these local screenshot-derived assets over unrelated stock imagery.
Preserve the user's selected stack instructions and visual fidelity requirements.""",
    ]

    image_index = 0
    for message in prompt_messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, str):
            prompt_sections.append(f"## {role}\n{content}")
            continue

        if not isinstance(content, list):
            continue

        text_parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                text_parts.append(str(part.get("text", "")))
                continue
            if part.get("type") != "image_url":
                continue

            image_url = part.get("image_url")
            if not isinstance(image_url, dict):
                continue
            raw_url = cast(object, image_url.get("url"))
            if not isinstance(raw_url, str):
                continue
            url = raw_url

            image_path = _write_data_url_image(url, workdir, image_index)
            if image_path is not None:
                image_paths.append(image_path)
                text_parts.append(f"[Attached image: {image_path.name}]")
                image_index += 1
            else:
                text_parts.append(f"[Image URL: {url}]")

        prompt_sections.append(f"## {role}\n" + "\n".join(text_parts))

    return "\n\n".join(prompt_sections), image_paths


def build_codex_exec_command(
    *,
    codex_path: str,
    workdir: Path,
    output_path: Path,
    prompt: str,
    image_paths: list[Path],
    model: str | None = None,
    profile: str | None = None,
) -> list[str]:
    command = [
        codex_path,
        "--ask-for-approval",
        "never",
        "--sandbox",
        "workspace-write",
        "exec",
        "--cd",
        str(workdir),
        "--skip-git-repo-check",
        "--ephemeral",
        "--json",
        "--output-last-message",
        str(output_path),
    ]

    if model:
        command.extend(["--model", model])
    if profile:
        command.extend(["--profile", profile])

    for image_path in image_paths:
        command.extend(["--image", str(image_path)])

    return command


def _looks_like_html_document(content: str) -> bool:
    normalized = content.lower()
    return "<html" in normalized and "</html>" in normalized


def _wrap_index_html(content: str) -> str:
    return f'<file path="index.html">\n{content}\n</file>'


def _local_asset_to_data_url(asset_path: Path) -> str | None:
    if not asset_path.exists() or not asset_path.is_file():
        return None

    mime_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_local_asset(workdir: Path, raw_path: str) -> Path | None:
    candidate = (workdir / unquote(raw_path)).resolve()
    try:
        candidate.relative_to(workdir.resolve())
    except ValueError:
        return None
    return candidate


def inline_local_asset_references(content: str, workdir: Path) -> str:
    def replace_attribute_or_url(match: re.Match[str]) -> str:
        asset_path = _resolve_local_asset(workdir, match.group("path"))
        data_url = _local_asset_to_data_url(asset_path) if asset_path else None
        if data_url is None:
            return match.group(0)
        return f"{match.group('prefix')}{data_url}{match.group('suffix')}"

    def replace_quoted_path(match: re.Match[str]) -> str:
        asset_path = _resolve_local_asset(workdir, match.group("path"))
        data_url = _local_asset_to_data_url(asset_path) if asset_path else None
        if data_url is None:
            return match.group(0)
        quote = match.group("quote")
        return f"{quote}{data_url}{quote}"

    content = LOCAL_ASSET_RE.sub(replace_attribute_or_url, content)
    return LOCAL_ASSET_STRING_RE.sub(replace_quoted_path, content)


def finalize_codex_assistant_text(assistant_text: str, workdir: Path) -> str:
    generated_index = workdir / "index.html"
    if generated_index.exists():
        html = generated_index.read_text(encoding="utf-8")
        if _looks_like_html_document(html):
            html = inline_local_asset_references(html, workdir)
            return _wrap_index_html(html)

    if "<file" in assistant_text and "</file>" in assistant_text:
        return assistant_text

    return assistant_text


class CodexCliProviderSession:
    def __init__(
        self,
        *,
        prompt_messages: list[ChatCompletionMessageParam],
        codex_path: str = "codex",
        runs_dir: Path,
        model: str | None = None,
        profile: str | None = None,
    ) -> None:
        self.prompt_messages = prompt_messages
        self.codex_path = codex_path
        self.runs_dir = runs_dir
        self.model = model
        self.profile = profile
        self.workdir = runs_dir / f"codex-cli-{uuid.uuid4().hex[:12]}"
        self.output_path = self.workdir / "last-message.md"

    async def stream_turn(self, on_event: EventSink) -> ProviderTurn:
        self.workdir.mkdir(parents=True, exist_ok=True)
        prompt, image_paths = prepare_codex_prompt_and_images(
            self.prompt_messages,
            self.workdir,
        )
        (self.workdir / "prompt.md").write_text(prompt, encoding="utf-8")

        command = build_codex_exec_command(
            codex_path=self.codex_path,
            workdir=self.workdir,
            output_path=self.output_path,
            prompt=prompt,
            image_paths=image_paths,
            model=self.model,
            profile=self.profile,
        )

        await on_event(
            StreamEvent(
                type="thinking_delta",
                text="Starting Codex CLI reconstruction worker...\n",
            )
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate(prompt.encode("utf-8"))
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        for line in stdout_text.splitlines():
            if line.strip():
                await on_event(StreamEvent(type="thinking_delta", text=f"{line}\n"))

        if process.returncode != 0:
            raise RuntimeError(
                "Codex CLI failed with exit code "
                f"{process.returncode}: {stderr_text.strip() or stdout_text.strip()}"
            )

        assistant_text = (
            self.output_path.read_text(encoding="utf-8")
            if self.output_path.exists()
            else stdout_text
        )
        assistant_text = finalize_codex_assistant_text(assistant_text, self.workdir)
        await on_event(StreamEvent(type="assistant_delta", text=assistant_text))
        return ProviderTurn(assistant_text=assistant_text, tool_calls=[])

    async def append_tool_results(
        self,
        turn: ProviderTurn,
        executed_tool_calls: list[ExecutedToolCall],
    ) -> None:
        return None

    def total_cost_usd(self) -> Optional[float]:
        return None

    async def close(self) -> None:
        return None
