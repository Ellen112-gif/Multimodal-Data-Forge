import json
import os

from src.config_loader import load_config
from src.adapters.visual_genome_adapter import VisualGenomeAdapter
from src.executors.local_executor import LocalExecutor
from src.executors.ray_executor import RayExecutor
from src.operators.semantic_dedup import SemanticDedup
from src.annotation.vlm_annotator import VLMAnnotator


CONFIG_PATH = "config/pipeline.yaml"


def load_samples(config):

    input_config = config["input"]

    source = input_config.get(
        "source",
        "visual_genome",
    ).lower()

    input_path = input_config["path"]

    if source == "visual_genome":

        adapter = VisualGenomeAdapter(
            input_path
        )

        return adapter.load()

    raise ValueError(
        f"Unknown input source: {source}"
    )


def save_samples(samples, path):

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
    ) as f:

        for sample in samples:

            f.write(
                json.dumps(
                    sample.to_dict(),
                    ensure_ascii=False,
                )
                + "\n"
            )


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
    ) as f:

        for annotation in annotations:

            f.write(
                json.dumps(
                    annotation.to_dict(),
                    ensure_ascii=False,
                )
                + "\n"
            )


def build_executor(config):

    executor_config = config.get(
        "executor",
        {},
    )

    executor_type = executor_config.get(
        "type",
        "local",
    ).lower()

    if executor_type == "local":

        return LocalExecutor(
            config=config
        )

    if executor_type == "ray":

        num_workers = executor_config.get(
            "num_workers",
            2,
        )

        batch_size = executor_config.get(
            "batch_size",
            2,
        )

        address = executor_config.get(
            "address",
            None,
        )

        return RayExecutor(
            config=config,
            num_workers=num_workers,
            batch_size=batch_size,
            address=address,
        )

    raise ValueError(
        f"Unknown executor type: {executor_type}"
    )


def append_dedup_metrics(
    metrics_path,
    dedup_metrics,
):

    try:

        with open(
            metrics_path,
            "r",
            encoding="utf-8",
        ) as f:

            metrics = json.load(f)

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ):

        metrics = {}

    metrics[
        "SemanticDedup"
    ] = dedup_metrics

    with open(
        metrics_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metrics,
            f,
            ensure_ascii=False,
            indent=2,
        )


def main():

    config = load_config(
        CONFIG_PATH
    )

    output_path = config[
        "output"
    ]["dataset_path"]

    metrics_path = config[
        "output"
    ]["metrics_path"]

    annotation_config = config.get(
        "annotation",
        {},
    )

    annotation_enabled = annotation_config.get(
        "enabled",
        False,
    )

    annotation_model = annotation_config.get(
        "model_name",
        "Salesforce/blip-image-captioning-base",
    )

    annotation_batch_size = annotation_config.get(
        "batch_size",
        4,
    )

    annotation_limit = annotation_config.get(
        "max_samples",
        10,
    )

    annotation_output_path = annotation_config.get(
        "output_path",
        "outputs/annotations.jsonl",
    )

    samples = load_samples(
        config
    )

    input_source = config[
        "input"
    ].get(
        "source",
        "visual_genome",
    ).lower()

    print(
        f"Input source: {input_source}"
    )

    print(
        f"Loaded: {len(samples)} "
        f"multimodal samples"
    )

    executor = build_executor(
        config
    )

    executor_config = config.get(
        "executor",
        {},
    )

    executor_type = executor_config.get(
        "type",
        "local",
    ).lower()

    if executor_type == "local":

        print(
            "Executor: LocalExecutor"
        )

    elif executor_type == "ray":

        num_workers = executor_config.get(
            "num_workers",
            2,
        )

        batch_size = executor_config.get(
            "batch_size",
            2,
        )

        print(
            "Executor: RayExecutor"
        )

        print(
            f"Workers: {num_workers}"
        )

        print(
            f"Batch size: {batch_size}"
        )

    processed_samples = executor.execute(
        samples
    )

    accepted_samples = [
        sample
        for sample in processed_samples
        if sample.status == "accepted"
    ]

    rejected_before_dedup = sum(
        sample.status == "rejected"
        for sample in processed_samples
    )

    print(
        "\nBefore semantic dedup:"
    )

    print(
        f"Accepted: "
        f"{len(accepted_samples)}"
    )

    print(
        f"Rejected: "
        f"{rejected_before_dedup}"
    )

    dedup = SemanticDedup(
        threshold=0.95,
        batch_size=32,
    )

    deduplicated_samples = dedup.process(
        accepted_samples
    )

    dedup.print_duplicate_pairs()

    duplicates_removed = (
        len(accepted_samples)
        - len(deduplicated_samples)
    )

    accepted_count = sum(
        sample.status == "accepted"
        for sample in processed_samples
    )

    rejected_count = sum(
        sample.status == "rejected"
        for sample in processed_samples
    )

    print(
        "\nSemantic Dedup"
    )

    print(
        f"Input accepted samples: "
        f"{len(accepted_samples)}"
    )

    print(
        f"Duplicates removed: "
        f"{duplicates_removed}"
    )

    print(
        f"Final accepted samples: "
        f"{accepted_count}"
    )

    print(
        f"Final rejected samples: "
        f"{rejected_count}"
    )

    if annotation_enabled:

        annotation_samples = (
            deduplicated_samples[
                :annotation_limit
            ]
        )

        print(
            "\nVLM Auto-Annotation"
        )

        print(
            f"Model: "
            f"{annotation_model}"
        )

        print(
            f"Samples selected for annotation: "
            f"{len(annotation_samples)}"
        )

        print(
            f"Annotation batch size: "
            f"{annotation_batch_size}"
        )

        annotator = VLMAnnotator(
            model_name=annotation_model,
            batch_size=annotation_batch_size,
        )

        annotations = (
            annotator.annotate_batch(
                annotation_samples
            )
        )

        annotation_success = sum(
            annotation.status == "success"
            for annotation in annotations
        )

        annotation_failed = (
            len(annotations)
            - annotation_success
        )

        save_annotations(
            annotations,
            annotation_output_path,
        )

        print(
            f"\nAnnotations generated: "
            f"{len(annotations)}"
        )

        print(
            f"Annotation success: "
            f"{annotation_success}"
        )

        print(
            f"Annotation failed: "
            f"{annotation_failed}"
        )

        print(
            f"Saved annotations: "
            f"{annotation_output_path}"
        )

    else:

        print(
            "\nVLM Auto-Annotation: disabled"
        )

    executor.print_metrics()

    executor.save_metrics(
        metrics_path
    )

    append_dedup_metrics(
        metrics_path,
        dedup.metrics,
    )

    save_samples(
        processed_samples,
        output_path,
    )

    print(
        f"\nSaved dataset: "
        f"{output_path}"
    )

    print(
        f"Saved metrics: "
        f"{metrics_path}"
    )


if __name__ == "__main__":
    main()