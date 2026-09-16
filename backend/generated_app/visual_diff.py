# pyright: reportUnknownVariableType=false
import base64
from io import BytesIO

from PIL import Image, ImageChops, ImageStat
from pydantic import BaseModel, ConfigDict, Field


class RegionSpec(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    region_id: str = Field(alias="regionId")
    label: str
    x: float
    y: float
    width: float
    height: float


class RegionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    region_id: str = Field(alias="regionId")
    label: str
    score: int
    mean_delta: float = Field(alias="meanDelta")
    repair_instruction: str = Field(alias="repairInstruction")


class VisualDiffReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    overall_score: int = Field(alias="overallScore")
    regions: list[RegionResult]
    repair_instructions: list[str] = Field(default_factory=list, alias="repairInstructions")


def default_regions() -> list[RegionSpec]:
    return [
        RegionSpec(regionId="full", label="Full page", x=0, y=0, width=1, height=1),
        RegionSpec(regionId="nav", label="Navigation", x=0, y=0, width=1, height=0.14),
        RegionSpec(regionId="hero", label="Hero", x=0, y=0.12, width=1, height=0.32),
        RegionSpec(regionId="middle", label="Middle content", x=0, y=0.38, width=1, height=0.34),
        RegionSpec(regionId="lower", label="Lower content", x=0, y=0.68, width=1, height=0.32),
    ]


def _decode_data_url(data_url: str) -> Image.Image:
    _, payload = data_url.split(",", 1) if "," in data_url else ("", data_url)
    image_bytes = base64.b64decode(payload)
    return Image.open(BytesIO(image_bytes)).convert("RGB")


def _crop_box(region: RegionSpec, width: int, height: int) -> tuple[int, int, int, int]:
    left = max(0, min(width, round(region.x * width)))
    top = max(0, min(height, round(region.y * height)))
    right = max(left + 1, min(width, round((region.x + region.width) * width)))
    bottom = max(top + 1, min(height, round((region.y + region.height) * height)))
    return left, top, right, bottom


def _score_region(reference: Image.Image, candidate: Image.Image, region: RegionSpec) -> RegionResult:
    width, height = reference.size
    box = _crop_box(region, width, height)
    reference_crop = reference.crop(box)
    candidate_crop = candidate.crop(box)
    delta = ImageChops.difference(reference_crop, candidate_crop)
    mean_delta = sum(ImageStat.Stat(delta).mean) / 3
    score = max(0, min(100, round(100 - (mean_delta / 255) * 100)))
    instruction = (
        ""
        if score >= 85
        else f"Rebuild {region.label} to better match source spacing, color, typography, and asset placement."
    )
    return RegionResult(
        regionId=region.region_id,
        label=region.label,
        score=score,
        meanDelta=round(mean_delta, 2),
        repairInstruction=instruction,
    )


def compare_visual_regions(
    reference_data_url: str,
    candidate_data_url: str,
    regions: list[RegionSpec] | None = None,
) -> VisualDiffReport:
    reference = _decode_data_url(reference_data_url)
    candidate = _decode_data_url(candidate_data_url).resize(reference.size)
    specs = regions or default_regions()
    results = [_score_region(reference, candidate, region) for region in specs]
    overall = round(sum(result.score for result in results) / len(results)) if results else 0
    instructions = [
        result.repair_instruction
        for result in results
        if result.repair_instruction
    ]
    return VisualDiffReport(
        overallScore=overall,
        regions=results,
        repairInstructions=instructions,
    )
