from src.schema.multimodal_sample import MultimodalSample
from src.operators.resolution_filter import ResolutionFilter


def make_sample(width, height):
    return MultimodalSample(
        sample_id="test_001",
        character="test",
        scene="test",
        dialogue="",
        image_prompt="test image",
        emotion="",
        action="",
        visual_style="real_image",
        image_path="test.jpg",
        width=width,
        height=height,
        status="validated",
    )


def test_resolution_accept():
    operator = ResolutionFilter(
        min_width=512,
        min_height=512,
    )

    sample = make_sample(
        width=1024,
        height=768,
    )

    result = operator.process(sample)

    assert result.status != "rejected"


def test_resolution_reject():
    operator = ResolutionFilter(
        min_width=512,
        min_height=512,
    )

    sample = make_sample(
        width=320,
        height=240,
    )

    result = operator.process(sample)

    assert result.status == "rejected"