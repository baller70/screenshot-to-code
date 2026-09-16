from typing import cast

from prompts.prompt_types import MirrorModeConfig, TargetFidelity


DEFAULT_MIRROR_MODE: MirrorModeConfig = {
    "enabled": False,
    "packet_mode": False,
    "sidecar_mode": False,
    "asset_registry": False,
    "route_registry": False,
    "backend_contract": False,
    "visual_repair": False,
    "target_fidelity": "standard",
}

_TARGET_FIDELITY_VALUES: set[TargetFidelity] = {"standard", "strict", "pixel"}


def parse_mirror_mode(raw_value: object) -> MirrorModeConfig:
    if not isinstance(raw_value, dict):
        return {
            "enabled": DEFAULT_MIRROR_MODE["enabled"],
            "packet_mode": DEFAULT_MIRROR_MODE["packet_mode"],
            "sidecar_mode": DEFAULT_MIRROR_MODE["sidecar_mode"],
            "asset_registry": DEFAULT_MIRROR_MODE["asset_registry"],
            "route_registry": DEFAULT_MIRROR_MODE["route_registry"],
            "backend_contract": DEFAULT_MIRROR_MODE["backend_contract"],
            "visual_repair": DEFAULT_MIRROR_MODE["visual_repair"],
            "target_fidelity": DEFAULT_MIRROR_MODE["target_fidelity"],
        }

    raw = cast(dict[str, object], raw_value)
    target_fidelity = raw.get("targetFidelity", "standard")
    if target_fidelity not in _TARGET_FIDELITY_VALUES:
        target_fidelity = "standard"

    return {
        "enabled": bool(raw.get("enabled", False)),
        "packet_mode": bool(raw.get("packetMode", False)),
        "sidecar_mode": bool(raw.get("sidecarMode", False)),
        "asset_registry": bool(raw.get("assetRegistry", False)),
        "route_registry": bool(raw.get("routeRegistry", False)),
        "backend_contract": bool(raw.get("backendContract", False)),
        "visual_repair": bool(raw.get("visualRepair", False)),
        "target_fidelity": cast(TargetFidelity, target_fidelity),
    }


def build_mirror_mode_prompt_block(
    mirror_mode: MirrorModeConfig | None,
    screenshot_count: int,
) -> str:
    if not mirror_mode or not mirror_mode["enabled"]:
        return ""

    fidelity = mirror_mode["target_fidelity"]
    lines: list[str] = [
        "## ImageGen 2.5 mirror contract",
        "",
        f"- Target fidelity: {fidelity}. Prioritize one-to-one visual reconstruction over redesign.",
        "- Treat the supplied ImageGen screens as product source material, not inspiration.",
        "- Preserve exact visible copy, hierarchy, spacing, color, typography, imagery, and interaction affordances.",
        "- Preserve each screen's first-viewport composition: nav density, sidebar/filter columns, hero/media placement, panel proportions, card/table counts, footer bands, and visible whitespace.",
        "- Do not collapse different screenshots into one generic layout pattern unless the screenshots themselves share that pattern.",
    ]

    if mirror_mode["packet_mode"]:
        lines.extend(
            [
                f"- Packet mode: interpret all {screenshot_count} uploaded image(s) as one coherent website/app packet.",
                "- Keep shared brand tokens, navigation, section rhythm, and repeated components consistent across screens.",
                "- Each uploaded image must become one named route or state in the same generated website/app, not a single blended page.",
            ]
        )

    if mirror_mode["route_registry"]:
        lines.extend(
            [
                "- Create a literal MIRROR_ROUTE_REGISTRY object/array in the generated code that maps each input screenshot to one route, tab, or major page section.",
                "- Each route registry entry must include inputIndex, route, label, viewportRole, sourceIntent, and majorRegions.",
                "- Name routes from the screen content when possible; otherwise use stable names such as page-1, page-2, page-3.",
            ]
        )

    if mirror_mode["sidecar_mode"]:
        lines.extend(
            [
                "- Sidecar mode: if the user's instructions include sidecar JSON, overlay notes, or screen metadata, treat those fields as authoritative over visual guessing.",
                "- Preserve sidecar identities for screen IDs, element IDs, bounds, text, asset refs, and interaction roles when supplied.",
            ]
        )

    if mirror_mode["asset_registry"]:
        lines.extend(
            [
                "- Create a literal MIRROR_ASSET_REGISTRY object/array for logos, photos, backgrounds, icons, badges, charts, and repeated artwork.",
                "- Each asset registry entry must include assetId, sourceInputIndexes, role, reusePolicy, and renderStrategy.",
                "- Reuse one stable asset identity for recurring visuals instead of recreating similar assets independently on each page.",
            ]
        )

    if mirror_mode["backend_contract"]:
        lines.extend(
            [
                "- Backend contract: mark forms, buttons, tables, filters, dashboards, login flows, booking flows, and other functional regions with clear handler/data names.",
                "- When backend behavior is visible but implementation details are unknown, generate deterministic local fixtures and name the API route or action that should back it later.",
            ]
        )

    if mirror_mode["visual_repair"]:
        lines.extend(
            [
                "- Prepare the output for visual repair: use stable data-mirror-id attributes on major sections, cards, nav items, CTAs, forms, image slots, and repeated elements.",
                "- Keep layout constants obvious in CSS so a later screenshot-diff pass can move, resize, or restyle individual elements without rewriting the page.",
                "- Favor explicit CSS variables, grid tracks, fixed aspect ratios, and named section wrappers over anonymous utility-only markup for mirrored regions.",
            ]
        )

    return "\n".join(lines)
