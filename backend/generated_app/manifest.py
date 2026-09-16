# pyright: reportUnknownVariableType=false
import ast
import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import BaseModel, ConfigDict, Field


class GeneratedAppRoute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input_index: int | None = Field(default=None, alias="inputIndex")
    route: str
    label: str
    viewport_role: str | None = Field(default=None, alias="viewportRole")
    source_intent: str | None = Field(default=None, alias="sourceIntent")
    major_regions: list[str] = Field(default_factory=list, alias="majorRegions")
    target_id: str | None = Field(default=None, alias="targetId")


class GeneratedAppAsset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(alias="assetId")
    source_input_indexes: list[int] = Field(default_factory=list, alias="sourceInputIndexes")
    role: str
    reuse_policy: str | None = Field(default=None, alias="reusePolicy")
    render_strategy: str | None = Field(default=None, alias="renderStrategy")
    occurrences: int = 1


class BackendContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    contract_id: str = Field(alias="contractId")
    kind: str
    label: str
    api_route: str = Field(alias="apiRoute")
    method: str = "POST"
    fields: list[str] = Field(default_factory=list)


class InteractionContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    interaction_id: str = Field(alias="interactionId")
    kind: str
    label: str
    target: str | None = None


class GeneratedAppScores(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    overall: int
    route_completeness: int = Field(alias="routeCompleteness")
    registry_completeness: int = Field(alias="registryCompleteness")
    mirror_id_coverage: int = Field(alias="mirrorIdCoverage")
    asset_reuse: int = Field(alias="assetReuse")
    backend_contract_coverage: int = Field(alias="backendContractCoverage")
    interaction_readiness: int = Field(alias="interactionReadiness")
    visual_evidence: int = Field(alias="visualEvidence")


class GeneratedAppManifest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    routes: list[GeneratedAppRoute] = Field(default_factory=list)
    assets: list[GeneratedAppAsset] = Field(default_factory=list)
    mirror_ids: list[str] = Field(default_factory=list, alias="mirrorIds")
    backend_contracts: list[BackendContract] = Field(
        default_factory=list,
        alias="backendContracts",
    )
    interactions: list[InteractionContract] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: GeneratedAppScores



REGISTRY_RE_TEMPLATE = r"MIRROR_{name}_REGISTRY\s*=\s*(\[[\s\S]*?\])\s*;"
UNQUOTED_KEY_RE = re.compile(r"(?<=[{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:")


def _parse_js_registry(html: str, name: str) -> list[dict[str, Any]] | None:
    match = re.search(REGISTRY_RE_TEMPLATE.format(name=name), html)
    if not match:
        return None

    raw = match.group(1)
    quoted = UNQUOTED_KEY_RE.sub(lambda item: f"'{item.group(1)}':", raw)
    try:
        parsed = ast.literal_eval(quoted)
    except (SyntaxError, ValueError):
        return None

    if not isinstance(parsed, list):
        return None
    return [entry for entry in parsed if isinstance(entry, dict)]


def _label_from_route(route: str) -> str:
    label = route.lstrip("#/").replace("-", " ").replace("_", " ").strip()
    return label.title() if label else "Page"


def _target_id(route: str) -> str | None:
    return route[1:] if route.startswith("#") and len(route) > 1 else None


def _extract_routes(html: str, soup: BeautifulSoup, warnings: list[str]) -> list[GeneratedAppRoute]:
    registry = _parse_js_registry(html, "ROUTE")
    if registry is not None:
        routes: list[GeneratedAppRoute] = []
        for entry in registry:
            route = str(entry.get("route") or "").strip()
            if not route:
                continue
            routes.append(
                GeneratedAppRoute(
                    inputIndex=entry.get("inputIndex"),
                    route=route,
                    label=str(entry.get("label") or _label_from_route(route)),
                    viewportRole=entry.get("viewportRole"),
                    sourceIntent=entry.get("sourceIntent"),
                    majorRegions=entry.get("majorRegions") or [],
                    targetId=_target_id(route),
                )
            )
        return routes

    warnings.append("Missing MIRROR_ROUTE_REGISTRY; inferred routes from DOM links.")
    seen: set[str] = set()
    routes = []
    for link in soup.select("a[href^='#']"):
        if not isinstance(link, Tag):
            continue
        href = link.get("href")
        if not isinstance(href, str) or href in seen or href == "#":
            continue
        seen.add(href)
        routes.append(
            GeneratedAppRoute(
                route=href,
                label=link.get_text(" ", strip=True) or _label_from_route(href),
                targetId=_target_id(href),
            )
        )
    return routes


def _extract_assets(html: str, soup: BeautifulSoup, warnings: list[str]) -> list[GeneratedAppAsset]:
    registry = _parse_js_registry(html, "ASSET")
    if registry is not None:
        assets: list[GeneratedAppAsset] = []
        for index, entry in enumerate(registry):
            asset_id = str(entry.get("assetId") or f"asset-{index + 1}")
            assets.append(
                GeneratedAppAsset(
                    assetId=asset_id,
                    sourceInputIndexes=entry.get("sourceInputIndexes") or [],
                    role=str(entry.get("role") or "asset"),
                    reusePolicy=entry.get("reusePolicy"),
                    renderStrategy=entry.get("renderStrategy"),
                )
            )
        return assets

    warnings.append("Missing MIRROR_ASSET_REGISTRY; inferred assets from DOM media.")
    assets = []
    for index, element in enumerate(soup.select("img[src], source[srcset], [style*='url(']")):
        role = "image" if element.name in {"img", "source"} else "background"
        assets.append(
            GeneratedAppAsset(
                assetId=f"inferred-{index + 1}",
                role=role,
                renderStrategy="dom-reference",
            )
        )
    return assets


def _extract_mirror_ids(soup: BeautifulSoup) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for element in soup.select("[data-mirror-id]"):
        value = element.get("data-mirror-id")
        if isinstance(value, str) and value and value not in seen:
            ids.append(value)
            seen.add(value)
    return ids


def _contract_label(element: Tag) -> str:
    label = element.get("aria-label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    text = element.get_text(" ", strip=True)
    return text[:80] if text else element.name


def _extract_backend_contracts(soup: BeautifulSoup) -> list[BackendContract]:
    contracts: list[BackendContract] = []
    for index, form in enumerate(soup.select("form")):
        if not isinstance(form, Tag):
            continue
        fields = []
        for field in form.select("input[name], select[name], textarea[name]"):
            name = field.get("name")
            if isinstance(name, str) and name:
                fields.append(name)
        api_route = form.get("data-api-route")
        if not isinstance(api_route, str) or not api_route:
            form_id = form.get("id")
            suffix = form_id if isinstance(form_id, str) and form_id else f"form-{index + 1}"
            api_route = f"/api/{suffix}"
        contracts.append(
            BackendContract(
                contractId=f"form-{index + 1}",
                kind="form",
                label=_contract_label(form),
                apiRoute=api_route,
                method=str(form.get("method") or "POST").upper(),
                fields=fields,
            )
        )
    return contracts


def _extract_interactions(soup: BeautifulSoup) -> list[InteractionContract]:
    interactions: list[InteractionContract] = []
    for index, link in enumerate(soup.select("a[href]")):
        if not isinstance(link, Tag):
            continue
        href = link.get("href")
        interactions.append(
            InteractionContract(
                interactionId=f"link-{index + 1}",
                kind="link",
                label=_contract_label(link),
                target=href if isinstance(href, str) else None,
            )
        )
    for index, button in enumerate(soup.select("button")):
        if not isinstance(button, Tag):
            continue
        interactions.append(
            InteractionContract(
                interactionId=f"button-{index + 1}",
                kind="button",
                label=_contract_label(button),
            )
        )
    return interactions


def _score(
    *,
    routes: list[GeneratedAppRoute],
    assets: list[GeneratedAppAsset],
    mirror_ids: list[str],
    backend_contracts: list[BackendContract],
    interactions: list[InteractionContract],
    has_route_registry: bool,
    has_asset_registry: bool,
) -> GeneratedAppScores:
    route_completeness = 20 if routes else 0
    registry_completeness = (10 if has_route_registry else 0) + (
        10 if has_asset_registry else 0
    )
    mirror_id_coverage = 15 if len(mirror_ids) >= max(1, len(routes)) else 8 if mirror_ids else 0
    asset_reuse = 15 if has_asset_registry and assets else 8 if assets else 0
    backend_contract_coverage = 15 if backend_contracts else 0
    interaction_readiness = 10 if interactions else 0
    visual_evidence = 0
    overall = sum(
        [
            route_completeness,
            registry_completeness,
            mirror_id_coverage,
            asset_reuse,
            backend_contract_coverage,
            interaction_readiness,
            visual_evidence,
        ]
    )
    return GeneratedAppScores(
        overall=overall,
        routeCompleteness=route_completeness,
        registryCompleteness=registry_completeness,
        mirrorIdCoverage=mirror_id_coverage,
        assetReuse=asset_reuse,
        backendContractCoverage=backend_contract_coverage,
        interactionReadiness=interaction_readiness,
        visualEvidence=visual_evidence,
    )


def analyze_generated_app_html(html: str) -> GeneratedAppManifest:
    soup = BeautifulSoup(html, "html.parser")
    warnings: list[str] = []
    has_route_registry = _parse_js_registry(html, "ROUTE") is not None
    has_asset_registry = _parse_js_registry(html, "ASSET") is not None

    routes = _extract_routes(html, soup, warnings)
    assets = _extract_assets(html, soup, warnings)
    mirror_ids = _extract_mirror_ids(soup)
    backend_contracts = _extract_backend_contracts(soup)
    interactions = _extract_interactions(soup)
    scores = _score(
        routes=routes,
        assets=assets,
        mirror_ids=mirror_ids,
        backend_contracts=backend_contracts,
        interactions=interactions,
        has_route_registry=has_route_registry,
        has_asset_registry=has_asset_registry,
    )

    return GeneratedAppManifest(
        routes=routes,
        assets=assets,
        mirrorIds=mirror_ids,
        backendContracts=backend_contracts,
        interactions=interactions,
        warnings=warnings,
        scores=scores,
    )
