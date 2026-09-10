from src.schema.multimodal_sample import MultimodalSample
from src.operators.base import BaseOperator


class SampleValidator(BaseOperator):

    def process(
        self,
        sample: MultimodalSample
    ) -> MultimodalSample:

        # 1. sample_id is required
        if not sample.sample_id:
            sample.status = "rejected"
            sample.reject_reason = "missing_sample_id"
            return sample

        # 2. image path is required
        if not sample.image_path:
            sample.status = "rejected"
            sample.reject_reason = "missing_image_path"
            return sample

        # 3. image-text alignment requires text
        if not sample.image_prompt:
            sample.status = "rejected"
            sample.reject_reason = "missing_image_prompt"
            return sample

        # All required fields passed
        sample.status = "validated"
        sample.reject_reason = None

        return sample