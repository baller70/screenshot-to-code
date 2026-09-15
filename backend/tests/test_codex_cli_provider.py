import base64
from pathlib import Path
from typing import cast

from openai.types.chat import ChatCompletionMessageParam

from agent.providers.codex_cli import (
    build_codex_exec_command,
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
    assert len(image_paths) == 1
    assert image_paths[0].read_bytes() == b"fake-png"
    assert image_paths[0].parent == tmp_path
