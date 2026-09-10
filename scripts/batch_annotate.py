import json
import os

from src.adapters.visual_genome_adapter import (
    VisualGenomeAdapter,
)

from src.annotation.vlm_annotator import (
    VLMAnnotator,
)


INPUT_PATH = (
    "data/visual_genome/samples.jsonl"
)

OUTPUT_PATH = (
    "outputs/annotations.jsonl"
)

NUM_SAMPLES = 5


def save_annotations(
    annotations,
    path,
):

    directory = os.path.dirname(
        path
    )

    if directory:

        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        for annotation in annotations:

            file.write(
                json.dumps(
                    annotation.to_dict(),
                    ensure_ascii=False,
                )
                + "\n"
            )


def main():

    adapter = VisualGenomeAdapter(
        INPUT_PATH
    )

    samples = adapter.load()

    samples = samples[
        :NUM_SAMPLES
    ]

    print(
        f"Loaded {len(samples)} "
        f"samples for annotation"
    )

    annotator = VLMAnnotator(batch_size=4)

    annotations = (
        annotator.annotate_batch(
            samples
        )
    )

    print(
        "\nAnnotation Results"
    )

    for annotation in annotations:

        print(
            f"\n{annotation.sample_id}"
        )

        print(
            f"Image: "
            f"{annotation.image_path}"
        )

        print(
            f"Caption: "
            f"{annotation.caption}"
        )

        print(
            f"Status: "
            f"{annotation.status}"
        )

        if annotation.error:

            print(
                f"Error: "
                f"{annotation.error}"
            )

    save_annotations(
        annotations,
        OUTPUT_PATH,
    )

    print(
        f"\nSaved annotations: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()