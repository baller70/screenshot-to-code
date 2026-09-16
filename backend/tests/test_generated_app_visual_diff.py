from io import BytesIO
import base64

from PIL import Image

from generated_app.visual_diff import RegionSpec, compare_visual_regions


def image_data_url(color: tuple[int, int, int], size: tuple[int, int] = (80, 80)) -> str:
    image = Image.new("RGB", size, color)
    output = BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def test_identical_images_score_100() -> None:
    image = image_data_url((20, 120, 220))

    report = compare_visual_regions(image, image)

    assert report.overall_score == 100
    assert all(region.score == 100 for region in report.regions)
    assert report.repair_instructions == []


def test_region_mismatch_identifies_weak_region() -> None:
    reference = image_data_url((255, 255, 255))
    candidate = image_data_url((0, 0, 0))

    report = compare_visual_regions(
        reference,
        candidate,
        regions=[RegionSpec(regionId="hero", label="Hero", x=0, y=0, width=1, height=1)],
    )

    assert report.overall_score == 0
    assert report.regions[0].region_id == "hero"
    assert report.regions[0].score == 0
    assert "Hero" in report.repair_instructions[0]


def test_default_regions_cover_page_structure() -> None:
    report = compare_visual_regions(
        image_data_url((10, 10, 10)),
        image_data_url((10, 10, 10)),
    )

    assert [region.region_id for region in report.regions] == [
        "full",
        "nav",
        "hero",
        "middle",
        "lower",
    ]
