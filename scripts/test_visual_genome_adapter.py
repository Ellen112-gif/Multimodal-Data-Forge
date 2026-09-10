from src.adapters.visual_genome_adapter import VisualGenomeAdapter
from src.config_loader import load_config
from src.operator_factory import build_operators
from src.pipeline import QualityPipeline


CONFIG_PATH = "config/pipeline.yaml"

VG_PATH = "data/visual_genome/samples.jsonl"


def main():

    # 1. Load config
    config = load_config(
        CONFIG_PATH
    )

    # 2. Load Visual Genome samples
    adapter = VisualGenomeAdapter(
        VG_PATH
    )

    samples = adapter.load()

    print(
        f"Loaded Visual Genome samples: "
        f"{len(samples)}"
    )

    # 3. Build existing operators
    operators = build_operators(
        config
    )

    # 4. Build existing quality pipeline
    pipeline = QualityPipeline(
        operators=operators
    )

    # 5. Process real multimodal samples
    processed_samples = []

    for sample in samples:

        sample = pipeline.process(
            sample
        )

        processed_samples.append(
            sample
        )

    # 6. Statistics
    accepted = sum(
        1
        for sample in processed_samples
        if sample.status == "accepted"
    )

    rejected = sum(
        1
        for sample in processed_samples
        if sample.status == "rejected"
    )

    print(
        f"Accepted: {accepted}"
    )

    print(
        f"Rejected: {rejected}"
    )

    # 7. Metrics
    pipeline.print_metrics()


if __name__ == "__main__":
    main()