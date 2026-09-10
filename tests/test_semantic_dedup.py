from src.schema.multimodal_sample import MultimodalSample
from src.operators.semantic_dedup import SemanticDedup


def make_sample(
    sample_id,
    width,
    height,
    blur_score,
    clip_score,
):
    sample = MultimodalSample(
        sample_id=sample_id,
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
        status="accepted",
    )

    sample.blur_score = blur_score
    sample.clip_score = clip_score

    return sample


def test_higher_quality_sample_scores_higher():

    dedup = SemanticDedup.__new__(
        SemanticDedup
    )

    low_quality = make_sample(
        sample_id="low",
        width=640,
        height=480,
        blur_score=120.0,
        clip_score=0.25,
    )

    high_quality = make_sample(
        sample_id="high",
        width=1920,
        height=1080,
        blur_score=400.0,
        clip_score=0.50,
    )

    low_score = dedup._quality_score(
        low_quality
    )

    high_score = dedup._quality_score(
        high_quality
    )

    assert high_score > low_score