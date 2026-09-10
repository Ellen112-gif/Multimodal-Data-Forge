from PIL import Image

import torch
from transformers import (
    BlipForConditionalGeneration,
    BlipProcessor,
)

from src.annotation.annotation_schema import (
    AnnotationResult,
)


class VLMAnnotator:

    def __init__(
        self,
        model_name="Salesforce/blip-image-captioning-base",
        batch_size=4,
    ):
        self.model_name = model_name
        self.batch_size = batch_size

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(
            f"VLMAnnotator device: {self.device}"
        )

        print(
            f"Loading VLM: {self.model_name}"
        )

        self.processor = (
            BlipProcessor.from_pretrained(
                self.model_name
            )
        )

        self.model = (
            BlipForConditionalGeneration
            .from_pretrained(
                self.model_name
            )
            .to(self.device)
        )

        self.model.eval()

    def annotate(self, sample):

        results = self._annotate_batch(
            [sample]
        )

        return results[0]

    def _annotate_batch(self, samples):

        if not samples:
            return []

        valid_samples = []
        images = []
        failed_results = []

        for sample in samples:

            try:

                with Image.open(
                    sample.image_path
                ) as image:

                    images.append(
                        image.convert("RGB")
                    )

                valid_samples.append(
                    sample
                )

            except Exception as error:

                failed_results.append(
                    AnnotationResult(
                        sample_id=sample.sample_id,
                        image_path=sample.image_path,
                        caption="",
                        model_name=self.model_name,
                        status="failed",
                        error=str(error),
                    )
                )

        successful_results = []

        if valid_samples:

            try:

                inputs = self.processor(
                    images=images,
                    return_tensors="pt",
                )

                inputs = {
                    key: value.to(self.device)
                    for key, value
                    in inputs.items()
                }

                with torch.no_grad():

                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=40,
                    )

                captions = (
                    self.processor.batch_decode(
                        outputs,
                        skip_special_tokens=True,
                    )
                )

                for sample, caption in zip(
                    valid_samples,
                    captions,
                ):

                    successful_results.append(
                        AnnotationResult(
                            sample_id=sample.sample_id,
                            image_path=sample.image_path,
                            caption=caption.strip(),
                            model_name=self.model_name,
                        )
                    )

            except Exception as error:

                for sample in valid_samples:

                    successful_results.append(
                        AnnotationResult(
                            sample_id=sample.sample_id,
                            image_path=sample.image_path,
                            caption="",
                            model_name=self.model_name,
                            status="failed",
                            error=str(error),
                        )
                    )

        results_by_id = {}

        for result in (
            successful_results
            + failed_results
        ):

            results_by_id[
                result.sample_id
            ] = result

        return [
            results_by_id[
                sample.sample_id
            ]
            for sample in samples
        ]

    def annotate_batch(self, samples):

        results = []

        total = len(samples)

        for start in range(
            0,
            total,
            self.batch_size,
        ):

            batch = samples[
                start:
                start + self.batch_size
            ]

            batch_results = (
                self._annotate_batch(
                    batch
                )
            )

            results.extend(
                batch_results
            )

            processed = min(
                start + len(batch),
                total,
            )

            print(
                f"Annotated: "
                f"{processed}/{total}"
            )

        return results