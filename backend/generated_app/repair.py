# pyright: reportUnknownVariableType=false
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from generated_app.manifest import GeneratedAppManifest, analyze_generated_app_html


class QualityGate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    gate_id: str = Field(alias="gateId")
    label: str
    ok: bool
    severity: str = "warning"
    message: str
    repair_instruction: str = Field(alias="repairInstruction")


class GeneratedAppAudit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    manifest: GeneratedAppManifest
    gates: list[QualityGate]
    repair_prompt: str = Field(alias="repairPrompt")


def _smoke_failures(smoke_report: dict[str, Any] | None) -> list[str]:
    if not smoke_report:
        return []
    failures = smoke_report.get("failures")
    if not isinstance(failures, list):
        return []
    return [str(failure) for failure in failures if str(failure).strip()]


def _gate(
    gate_id: str,
    label: str,
    ok: bool,
    message: str,
    repair_instruction: str,
    severity: str = "warning",
) -> QualityGate:
    return QualityGate(
        gateId=gate_id,
        label=label,
        ok=ok,
        severity=severity,
        message=message,
        repairInstruction=repair_instruction,
    )


def build_quality_gates(
    manifest: GeneratedAppManifest,
    smoke_report: dict[str, Any] | None = None,
) -> list[QualityGate]:
    failures = _smoke_failures(smoke_report)
    return [
        _gate(
            "route-registry",
            "Route registry",
            bool(manifest.routes) and manifest.scores.registry_completeness >= 10,
            "Every source image should map to a stable page route or major section.",
            "Add or repair MIRROR_ROUTE_REGISTRY with one entry per source screenshot, including route, label, viewportRole, sourceIntent, and majorRegions.",
            "error",
        ),
        _gate(
            "asset-registry",
            "Asset registry",
            bool(manifest.assets) and manifest.scores.asset_reuse >= 15,
            "Reusable source-image assets need stable IDs so repeated logos, heroes, icons, and textures stay consistent across pages.",
            "Add or repair MIRROR_ASSET_REGISTRY with assetId, sourceInputIndexes, role, reusePolicy, renderStrategy, and occurrence notes.",
        ),
        _gate(
            "mirror-id-coverage",
            "Mirror IDs",
            manifest.scores.mirror_id_coverage >= 15,
            "Important layout regions should be traceable back to the source image.",
            "Add data-mirror-id attributes to every top-level page, hero, nav, card group, form, repeated asset, and important CTA.",
        ),
        _gate(
            "backend-contracts",
            "Backend contracts",
            bool(manifest.backend_contracts),
            "Forms and action surfaces should export backend endpoints instead of becoming dead HTML.",
            "Add real form tags with named fields and data-api-route attributes for each submission/action surface.",
        ),
        _gate(
            "interaction-contracts",
            "Interactions",
            bool(manifest.interactions),
            "Navigation, buttons, and forms should be testable after generation.",
            "Use real anchors, buttons, and forms for all visible interactive affordances; avoid decorative div-only controls.",
        ),
        _gate(
            "smoke-report",
            "Smoke report",
            not failures,
            "Automated browser smoke checks should pass on every generated route and form.",
            "Fix the listed smoke failures first: " + "; ".join(failures[:8]) if failures else "Run the generated-app smoke script after each rebuild and keep failures empty.",
            "error" if failures else "info",
        ),
    ]


def build_repair_prompt(
    manifest: GeneratedAppManifest,
    gates: list[QualityGate],
    smoke_report: dict[str, Any] | None = None,
) -> str:
    failed_gates = [gate for gate in gates if not gate.ok]
    route_lines = [
        f"- {route.route}: {route.label} ({route.viewport_role or 'unknown role'})"
        for route in manifest.routes
    ]
    failure_lines = [f"- {failure}" for failure in _smoke_failures(smoke_report)]
    gate_lines = [
        f"- [{gate.severity}] {gate.label}: {gate.repair_instruction}"
        for gate in failed_gates
    ]

    return "\n".join(
        [
            "# Generated App Mirror Repair Packet",
            "",
            "You are repairing an ImageGen 2.5 screenshot-to-code website mirror. Preserve the visual match first, then repair structure and functionality without changing the intended design.",
            "",
            "## Current Scores",
            f"- Overall: {manifest.scores.overall}",
            f"- Route completeness: {manifest.scores.route_completeness}",
            f"- Registry completeness: {manifest.scores.registry_completeness}",
            f"- Mirror ID coverage: {manifest.scores.mirror_id_coverage}",
            f"- Asset reuse: {manifest.scores.asset_reuse}",
            f"- Backend contract coverage: {manifest.scores.backend_contract_coverage}",
            f"- Interaction readiness: {manifest.scores.interaction_readiness}",
            "",
            "## Routes",
            *(route_lines or ["- No routes found."]),
            "",
            "## Required Repairs",
            *(gate_lines or ["- No required repairs. Keep the current structure intact."]),
            "",
            "## Smoke Failures",
            *(failure_lines or ["- None reported."]),
            "",
            "## Output Rules",
            "- Return the complete updated HTML.",
            "- Keep existing route IDs, data-mirror-id values, registries, copy, and assets unless the repair requires a precise change.",
            "- Do not collapse a multi-page website into one static hero.",
            "- Every visible form/action must have a data-api-route and named fields.",
        ]
    )


def audit_generated_app_html(
    html: str,
    smoke_report: dict[str, Any] | None = None,
) -> GeneratedAppAudit:
    manifest = analyze_generated_app_html(html)
    gates = build_quality_gates(manifest, smoke_report)
    return GeneratedAppAudit(
        manifest=manifest,
        gates=gates,
        repairPrompt=build_repair_prompt(manifest, gates, smoke_report),
    )
