from src.schema.multimodal_sample import MultimodalSample
from src.operators.validator import SampleValidator


def make_sample():
    return MultimodalSample(
        sample_id="test_001",
        character="test",
        scene="test scene",
        dialogue="",
        image_prompt="a dog in a field",
        emotion="",
        action="",
        visual_style="real_image",
        image_path="test.jpg",
        width=640,
        height=480,
        status="pending",
    )


def test_valid_sample():
    validator = SampleValidator()

    sample = make_sample()
    result = validator.process(sample)

    assert result.status == "validated"
    assert result.reject_reason is None


def test_missing_image_path():
    validator = SampleValidator()

    sample = make_sample()
    sample.image_path = None

    result = validator.process(sample)

    assert result.status == "rejected"