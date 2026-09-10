from PIL import Image

import torch
import torch.nn.functional as F
from transformers import CLIPModel, CLIPProcessor


class SemanticDedup:

    def __init__(
        self,
        threshold=0.95,
        model_name="openai/clip-vit-base-patch32",
        batch_size=32,
    ):
        self.threshold = threshold
        self.batch_size = batch_size

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(
            f"SemanticDedup device: {self.device}"
        )

        self.model = CLIPModel.from_pretrained(
            model_name
        ).to(self.device)

        self.processor = CLIPProcessor.from_pretrained(
            model_name
        )

        self.model.eval()

        self.metrics = {
            "input_samples": 0,
            "duplicates_removed": 0,
            "output_samples": 0,
        }

        self.duplicate_pairs = []

    def _encode_batch(self, samples):

        images = []

        for sample in samples:

            with Image.open(
                sample.image_path
            ) as image:

                images.append(
                    image.convert("RGB")
                )

        inputs = self.processor(
            images=images,
            return_tensors="pt",
        )

        pixel_values = inputs[
            "pixel_values"
        ].to(self.device)

        with torch.no_grad():

            embeddings = (
                self.model.get_image_features(
                    pixel_values=pixel_values
                )
            )

        embeddings = F.normalize(
            embeddings,
            p=2,
            dim=1,
        )

        return embeddings.cpu()

    def _encode_images(self, samples):

        batches = []

        for start in range(
            0,
            len(samples),
            self.batch_size,
        ):

            batch = samples[
                start:
                start + self.batch_size
            ]

            embeddings = self._encode_batch(
                batch
            )

            batches.append(
                embeddings
            )

        return torch.cat(
            batches,
            dim=0,
        )

    def _quality_score(self, sample):

        width = sample.width or 0
        height = sample.height or 0

        resolution = width * height

        blur_score = getattr(
            sample,
            "blur_score",
            0.0,
        ) or 0.0

        clip_score = getattr(
            sample,
            "clip_score",
            0.0,
        ) or 0.0

        resolution_score = min(
            resolution / (1920 * 1080),
            1.0,
        )

        sharpness_score = min(
            blur_score / 500.0,
            1.0,
        )

        alignment_score = min(
            max(clip_score, 0.0),
            1.0,
        )

        quality_score = (
            0.2 * resolution_score
            + 0.3 * sharpness_score
            + 0.5 * alignment_score
        )

        return quality_score

    def process(self, samples):

        if not samples:
            return []

        self.metrics[
            "input_samples"
        ] = len(samples)

        self.duplicate_pairs = []

        embeddings = self._encode_images(
            samples
        )

        similarity_matrix = (
            embeddings @ embeddings.T
        )

        kept_indices = []

        rejected_indices = set()

        for index in range(
            len(samples)
        ):

            duplicate_index = None
            duplicate_score = None

            for kept_index in kept_indices:

                similarity = similarity_matrix[
                    index,
                    kept_index
                ].item()

                if similarity >= self.threshold:

                    duplicate_index = (
                        kept_index
                    )

                    duplicate_score = (
                        similarity
                    )

                    break

            if duplicate_index is None:

                kept_indices.append(
                    index
                )

                continue

            current_quality = (
                self._quality_score(
                    samples[index]
                )
            )

            kept_quality = (
                self._quality_score(
                    samples[
                        duplicate_index
                    ]
                )
            )

            if current_quality > kept_quality:

                kept_indices.remove(
                    duplicate_index
                )

                kept_indices.append(
                    index
                )

                rejected_indices.add(
                    duplicate_index
                )

                kept_sample = samples[
                    index
                ]

                rejected_sample = samples[
                    duplicate_index
                ]

                kept_quality_score = (
                    current_quality
                )

                rejected_quality_score = (
                    kept_quality
                )

            else:

                rejected_indices.add(
                    index
                )

                kept_sample = samples[
                    duplicate_index
                ]

                rejected_sample = samples[
                    index
                ]

                kept_quality_score = (
                    kept_quality
                )

                rejected_quality_score = (
                    current_quality
                )

            self.duplicate_pairs.append({
                "duplicate_sample_id":
                    rejected_sample.sample_id,

                "kept_sample_id":
                    kept_sample.sample_id,

                "similarity":
                    duplicate_score,

                "duplicate_quality":
                    rejected_quality_score,

                "kept_quality":
                    kept_quality_score,
            })

        deduplicated_samples = []

        for index, sample in enumerate(
            samples
        ):

            if index in rejected_indices:

                sample.status = "rejected"

                sample.reject_reason = (
                    "semantic_duplicate"
                )

            else:

                deduplicated_samples.append(
                    sample
                )

        self.metrics[
            "duplicates_removed"
        ] = len(
            rejected_indices
        )

        self.metrics[
            "output_samples"
        ] = len(
            deduplicated_samples
        )

        return deduplicated_samples

    def print_duplicate_pairs(self):

        if not self.duplicate_pairs:

            print(
                "\nNo semantic duplicates found."
            )

            return

        print(
            "\nQuality-Aware Duplicate Selection"
        )

        for pair in self.duplicate_pairs:

            print(
                f"{pair['duplicate_sample_id']} "
                f"→ "
                f"{pair['kept_sample_id']} "
                f"| similarity="
                f"{pair['similarity']:.4f} "
                f"| rejected_quality="
                f"{pair['duplicate_quality']:.4f} "
                f"| kept_quality="
                f"{pair['kept_quality']:.4f}"
            )