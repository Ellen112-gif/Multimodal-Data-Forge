import copy
import csv
import os
import statistics
import time

from src.config_loader import load_config
from src.adapters.visual_genome_adapter import VisualGenomeAdapter
from src.executors.local_executor import LocalExecutor
from src.executors.ray_executor import RayExecutor


CONFIG_PATH = "config/pipeline.yaml"
OUTPUT_PATH = "benchmarks/scaling_results.csv"

DATASET_SIZES = (100, 500, 1000)
WORKERS = (2, 4)
NUM_RUNS = 3
BATCH_SIZE = 2


def load_samples(config):
    adapter = VisualGenomeAdapter(config["input"]["path"])
    return adapter.load()


def run_local(config, samples):
    executor = LocalExecutor(config=config)
    data = copy.deepcopy(samples)

    start = time.perf_counter()
    processed = executor.execute(data)
    elapsed = time.perf_counter() - start

    return processed, elapsed


def run_ray(config, samples, workers):
    executor = RayExecutor(
        config=config,
        num_workers=workers,
        batch_size=BATCH_SIZE,
    )

    executor.start()

    data = copy.deepcopy(samples)

    start = time.perf_counter()
    processed = executor.execute(
        data,
        keep_alive=True,
    )
    elapsed = time.perf_counter() - start

    executor.shutdown()

    return processed, elapsed


def benchmark_config(
    config,
    samples,
    executor_name,
    workers=None,
):
    times = []
    throughputs = []
    accepted = 0
    rejected = 0

    for run in range(1, NUM_RUNS + 1):
        print(
            f"\n{executor_name} | "
            f"{len(samples)} samples | "
            f"Run {run}/{NUM_RUNS}"
        )

        if executor_name == "Local":
            processed, elapsed = run_local(
                config,
                samples,
            )
        else:
            processed, elapsed = run_ray(
                config,
                samples,
                workers,
            )

        throughput = len(processed) / elapsed

        accepted = sum(
            s.status == "accepted"
            for s in processed
        )

        rejected = sum(
            s.status == "rejected"
            for s in processed
        )

        times.append(elapsed)
        throughputs.append(throughput)

        print(
            f"Time: {elapsed:.2f}s | "
            f"Throughput: {throughput:.2f} samples/s | "
            f"Accepted: {accepted} | "
            f"Rejected: {rejected}"
        )

    return {
        "samples": len(samples),
        "executor": executor_name,
        "runs": NUM_RUNS,
        "median_time": statistics.median(times),
        "median_throughput": statistics.median(
            throughputs
        ),
        "accepted": accepted,
        "rejected": rejected,
    }


def save_csv(results):
    os.makedirs(
        os.path.dirname(OUTPUT_PATH),
        exist_ok=True,
    )

    fieldnames = [
        "samples",
        "executor",
        "runs",
        "median_time",
        "median_throughput",
        "accepted",
        "rejected",
    ]

    with open(
        OUTPUT_PATH,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(results)


def print_summary(results):
    print("\nFinal Scaling Benchmark")

    print(
        f"{'Samples':>8}"
        f"{'Executor':>12}"
        f"{'Runs':>8}"
        f"{'Median(s)':>14}"
        f"{'Throughput':>16}"
        f"{'Accepted':>11}"
        f"{'Rejected':>11}"
    )

    for r in results:
        print(
            f"{r['samples']:>8}"
            f"{r['executor']:>12}"
            f"{r['runs']:>8}"
            f"{r['median_time']:>14.2f}"
            f"{r['median_throughput']:>16.2f}"
            f"{r['accepted']:>11}"
            f"{r['rejected']:>11}"
        )


def main():
    config = load_config(CONFIG_PATH)
    all_samples = load_samples(config)

    print(
        f"Loaded {len(all_samples)} "
        f"Visual Genome samples"
    )

    results = []

    for size in DATASET_SIZES:
        samples = all_samples[:size]

        results.append(
            benchmark_config(
                config=config,
                samples=samples,
                executor_name="Local",
            )
        )

        for workers in WORKERS:
            results.append(
                benchmark_config(
                    config=config,
                    samples=samples,
                    executor_name=f"Ray-{workers}W",
                    workers=workers,
                )
            )

    print_summary(results)
    save_csv(results)

    print(
        f"\nSaved benchmark results: "
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()