from types import SimpleNamespace
from typing import Any, Dict, List, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai.types.chat import ChatCompletionMessageParam

from llm import Llm
from routes.generate_code import (
    CodeGenerationMiddleware,
    ExtractedParams,
    PipelineContext,
)


@pytest.mark.asyncio
async def test_all_failed_variants_surface_first_variant_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeModelSelectionStage:
        def __init__(self, throw_error: object) -> None:
            pass

        async def select_models(self, **kwargs: object) -> List[Llm]:
            return [Llm.CODEX_CLI]

    class FakeAgenticGenerationStage:
        variant_errors = {0: "Codex CLI failed with exit code 1: usage limit"}

        def __init__(self, **kwargs: object) -> None:
            pass

        async def process_variants(
            self,
            variant_models: List[Llm],
            prompt_messages: List[ChatCompletionMessageParam],
        ) -> Dict[int, str]:
            return {}

    monkeypatch.setattr(
        "routes.generate_code.ModelSelectionStage",
        FakeModelSelectionStage,
    )
    monkeypatch.setattr(
        "routes.generate_code.AgenticGenerationStage",
        FakeAgenticGenerationStage,
    )

    context = PipelineContext(websocket=MagicMock())
    throw_error = AsyncMock()
    context.ws_comm = cast(
        Any,
        SimpleNamespace(
            send_message=AsyncMock(),
            throw_error=throw_error,
        ),
    )
    context.extracted_params = ExtractedParams(
        stack="html_tailwind",
        input_mode="image",
        should_generate_images=True,
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        replicate_api_key=None,
        openai_base_url=None,
        generation_type="create",
        prompt={"text": "Build", "images": ["data:image/png;base64,abc"], "videos": []},
        history=[],
        file_state=None,
        option_codes=[],
    )
    context.prompt_messages = []

    await CodeGenerationMiddleware().process(context, AsyncMock())

    throw_error.assert_awaited_once_with(
        "Codex CLI failed with exit code 1: usage limit"
    )
