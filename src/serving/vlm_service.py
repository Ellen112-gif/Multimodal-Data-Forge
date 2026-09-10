from types import SimpleNamespace

from ray import serve

from src.annotation.vlm_annotator import VLMAnnotator


@serve.deployment(
    num_replicas=1,
)
class VLMService:

    def __init__(self):

        self.annotator = VLMAnnotator(
            model_name=(
                "Salesforce/"
                "blip-image-captioning-base"
            ),
            batch_size=1,
        )

    async def __call__(
        self,
        request,
    ):

        data = await request.json()

        sample_id = data.get(
            "sample_id",
            "online_sample",
        )

        image_path = data.get(
            "image_path"
        )

        if not image_path:

            return {
                "status": "failed",
                "error": (
                    "image_path is required"
                ),
            }

        sample = SimpleNamespace(
            sample_id=sample_id,
            image_path=image_path,
        )

        result = self.annotator.annotate(
            sample
        )

        return result.to_dict()


app = VLMService.bind()