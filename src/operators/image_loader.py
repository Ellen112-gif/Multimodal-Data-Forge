import os
import cv2

from src.operators.base import BaseOperator
from src.schema.multimodal_sample import MultimodalSample


class ImageLoader(BaseOperator):

    def __init__(self, image_dir="outputs/images"):
        self.image_dir = image_dir

    def process(
        self,
        sample: MultimodalSample
    ) -> MultimodalSample:

        # 1. Prefer image_path already provided by the sample
        if sample.image_path:
            image_path = sample.image_path

        # 2. Fallback for synthetic data
        else:
            image_path = os.path.join(
                self.image_dir,
                f"{sample.sample_id}.jpg"
            )

        # 3. Check whether image exists
        if not os.path.exists(image_path):
            sample.status = "rejected"
            sample.reject_reason = "missing_image"
            return sample

        # 4. Read image
        image = cv2.imread(image_path)

        if image is None:
            sample.status = "rejected"
            sample.reject_reason = "invalid_image"
            return sample

        # 5. Update image metadata
        height, width = image.shape[:2]

        sample.image_path = image_path
        sample.width = width
        sample.height = height

        return sample