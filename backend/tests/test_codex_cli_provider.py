import base64
from pathlib import Path
from typing import cast

from openai.types.chat import ChatCompletionMessageParam

from agent.providers.codex_cli import (
    build_codex_exec_command,
    finalize_codex_assistant_text,
    prepare_codex_prompt_and_images,
)


def test_build_codex_exec_command_uses_safe_noninteractive_defaults(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(b"png")
    output_path = tmp_path / "last-message.md"

    command = build_codex_exec_command(
        codex_path="codex",
        workdir=tmp_path,
        output_path=output_path,
        prompt="Build this UI.",
        image_paths=[image_path],
        model="gpt-5.6-sol",
        profile="factory",
    )

    assert command[:2] == ["codex", "--ask-for-approval"]
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert "exec" in command
    assert "--json" in command
    assert "--ephemeral" in command
    assert "--skip-git-repo-check" in command
    assert command[command.index("--image") + 1] == str(image_path)
    assert command[command.index("--output-last-message") + 1] == str(output_path)
    assert command[command.index("--model") + 1] == "gpt-5.6-sol"
    assert command[command.index("--profile") + 1] == "factory"
    assert "Build this UI." not in command


def test_build_codex_exec_command_does_not_put_prompt_after_variadic_image_args(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(b"png")

    command = build_codex_exec_command(
        codex_path="codex",
        workdir=tmp_path,
        output_path=tmp_path / "last-message.md",
        prompt="Build this UI.",
        image_paths=[image_path],
    )

    image_arg_index = command.index("--image") + 1

    assert command[image_arg_index:] == [str(image_path)]
    assert "Build this UI." not in command


def test_prepare_codex_prompt_writes_data_url_images_and_preserves_text(
    tmp_path: Path,
) -> None:
    image_payload = base64.b64encode(b"fake-png").decode("ascii")
    messages = cast(
        list[ChatCompletionMessageParam],
        [
            {"role": "system", "content": "System rules"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_payload}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": "Make it exact."},
                ],
            },
        ],
    )

    prompt, image_paths = prepare_codex_prompt_and_images(messages, tmp_path)

    assert "System rules" in prompt
    assert "Make it exact." in prompt
    assert "Screenshot-to-Code Factory" in prompt
    assert "Create local asset files" in prompt
    assert len(image_paths) == 1
    assert image_paths[0].read_bytes() == b"fake-png"
    assert image_paths[0].parent == tmp_path


def test_finalize_codex_assistant_text_returns_generated_index_file(
    tmp_path: Path,
) -> None:
    index_html = tmp_path / "index.html"
    index_html.write_text(
        "<!DOCTYPE html><html><body>Built site</body></html>",
        encoding="utf-8",
    )

    assistant_text = finalize_codex_assistant_text(
        "Built index.html as requested.",
        tmp_path,
    )

    assert assistant_text.startswith('<file path="index.html">')
    assert "<body>Built site</body>" in assistant_text
    assert assistant_text.endswith("</file>")


def test_finalize_codex_assistant_text_prefers_real_html_over_summary_file_block(
    tmp_path: Path,
) -> None:
    index_html = tmp_path / "index.html"
    index_html.write_text(
        "<!DOCTYPE html><html><body>Real generated site</body></html>",
        encoding="utf-8",
    )

    assistant_text = finalize_codex_assistant_text(
        '<file path="index.html">Completed runnable website.</file>',
        tmp_path,
    )

    assert "<body>Real generated site</body>" in assistant_text
    assert "Completed runnable website" not in assistant_text


def test_finalize_codex_assistant_text_inlines_generated_local_image_assets(
    tmp_path: Path,
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "hero.png").write_bytes(b"fake-png")
    (assets_dir / "card.jpg").write_bytes(b"fake-jpg")
    (tmp_path / "index.html").write_text(
        (
            "<!DOCTYPE html><html><head><style>"
            ".hero{background-image:url('assets/hero.png')}"
            "</style></head><body>"
            '<img src="assets/card.jpg" alt="Card">'
            "</body></html>"
        ),
        encoding="utf-8",
    )

    assistant_text = finalize_codex_assistant_text(
        "Built index.html with assets.",
        tmp_path,
    )

    assert "data:image/png;base64,ZmFrZS1wbmc=" in assistant_text
    assert "data:image/jpeg;base64,ZmFrZS1qcGc=" in assistant_text
    assert "assets/hero.png" not in assistant_text
    assert "assets/card.jpg" not in assistant_text
