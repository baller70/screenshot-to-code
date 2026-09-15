from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam

from prompts.prompt_types import Stack
from prompts import system_prompt
from prompts.design_system import build_design_system_prompt_block
from prompts.policies import build_selected_stack_policy, build_user_image_policy

def build_image_prompt_messages(
    image_data_urls: list[str],
    stack: Stack,
    text_prompt: str,
    image_generation_enabled: bool,
    design_system: str | None = None,
) -> list[ChatCompletionMessageParam]:
    image_policy = build_user_image_policy(image_generation_enabled)
    selected_stack = build_selected_stack_policy(stack)
    design_system_block = build_design_system_prompt_block(design_system)
    website_mode_instruction = (
        """
Build a complete navigable website from the provided screenshots.
Each screenshot is a distinct page, route, or major section in the final website.
Preserve the supplied screenshot order as the default site map unless the user's instructions explicitly name a different order.
Do not output a gallery of screenshots, static examples, or disconnected mockups.
The generated result must be a runnable website that users can click through in the preview.
"""
        if len(image_data_urls) > 1
        else "Generate code for a web page that looks exactly like the provided screenshot."
    )

    user_prompt = f"""
{website_mode_instruction}

{selected_stack}
{design_system_block}

## Replication instructions

- Make sure the web page looks exactly like the screenshot.
- Use the exact text from the screenshot.
- Since our goal is to make the web page look as close to the screenshot as possible, we need to extract the exact image assets where possible and generate images for the assets that are not extractable.
- Extracting assets can be done with the extract_assets tool. After extracting assets, make sure to inspect the extracted image closely to ensure that it is what we want.
- When available, use edit_images for asset edits such as removing unwanted elements, batching independent edits into one call.
- If an extracted or supplied asset is visibly low-resolution or pixelated and must render larger, upscale it with edit_images—not CSS stretching or generate_images.
- If an asset in the original screenshot is not extractable (for example, occluded by other objects or is the background), when available, use generate_images to create image URLs from prompts (you may pass multiple prompts).

- {image_policy}

## Multiple screenshots

If multiple screenshots are provided, treat them as a website build packet:

- Make each screenshot a distinct page, route, tab, or major section and link them through realistic navigation.
- Infer page roles from the visuals and user prompt when possible: landing/home, about, programs, services, pricing, contact, dashboard, detail page, etc.
- If page roles are ambiguous, name them by position such as Page 1, Page 2, Page 3, but still build one coherent navigable website.
- Do not output a gallery of screenshots or a comparison page.
- Do not ask the user to copy and paste code; the generated preview is the website.
- For mobile screenshots, do not include the device frame or browser chrome; focus only on the actual UI mockups.
"""

    # Add additional instructions provided by the user
    if text_prompt.strip():
        user_prompt = f"{user_prompt}\n\nAdditional instructions: {text_prompt}"

    user_content: list[ChatCompletionContentPartParam] = []
    for image_data_url in image_data_urls:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_data_url, "detail": "high"},
            }
        )
    user_content.append(
        {
            "type": "text",
            "text": user_prompt,
        }
    )
    return [
        {
            "role": "system",
            "content": system_prompt.SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
