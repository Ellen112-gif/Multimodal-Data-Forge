import copy
import time

from src.config_loader import load_config
from src.adapters.visual_genome_adapter import VisualGenomeAdapter
from src.executors.local_executor import LocalExecutor
from src.executors.ray_executor import RayExecutor


CONFIG_PATH = "config/pipeline.yaml"


def load_samples(config):
    adapter = VisualGenomeAdapter(config["input"]["path"])
    return adapter.load()


def count_results(samples):
    accepted = sum(s.status == "accepted" for s in samples)
    rejected = sum(s.status == "rejected" for s in samples)
    return accepted, rejected


def result(name, mode, samples, elapsed):
    accepted, rejected = count_results(samples)

    return {
        "executor": name,
        "mode": mode,
        "samples": len(samples),
        "time": elapsed,
        "throughput": len(samples) / elapsed,
        "accepted": accepted,
        "rejected": rejected,
    }


def benchmark_local(config, samples):
    results = []

    # Cold start: include pipeline/model initialization.
    data = copy.deepcopy(samples)

    start = time.perf_counter()

    executor = LocalExecutor(config)
    processed = executor.execute(data)

    elapsed = time.perf_counter() - start

    results.append(
        result("Local", "Cold", processed, elapsed)
    )

    # Steady state: executor/model already initialized.
    executor = LocalExecutor(config)
    data = copy.deepcopy(samples)

    start = time.perf_counter()

    processed = executor.execute(data)

    elapsed = time.perf_counter() - start

    results.append(
        result("Local", "Steady", processed, elapsed)
    )

    return results


def benchmark_ray(config, samples, workers):
    results = []

    # Cold start: include Ray + actors + model initialization.
    data = copy.deepcopy(samples)

    executor = RayExecutor(
        config=config,
        num_workers=workers,
        batch_size=2,
    )

    start = time.perf_counter()

    processed = executor.execute(data)

    elapsed = time.perf_counter() - start

    results.append(
        result(f"Ray-{workers}W", "Cold", processed, elapsed)
    )

    # Steady state: Ray + actors + models already initialized.
    executor = RayExecutor(
        config=config,
        num_workers=workers,
        batch_size=2,
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

    results.append(
        result(f"Ray-{workers}W", "Steady", processed, elapsed)
    )

    return results


def print_summary(results):
    print("\nBenchmark Summary")

    print(
        f"{'Executor':<12}"
        f"{'Mode':<10}"
        f"{'Samples':>9}"
        f"{'Time(s)':>12}"
        f"{'Throughput':>16}"
        f"{'Accepted':>11}"
        f"{'Rejected':>11}"
    )

    for r in results:
        print(
            f"{r['executor']:<12}"
            f"{r['mode']:<10}"
            f"{r['samples']:>9}"
            f"{r['time']:>12.2f}"
            f"{r['throughput']:>16.2f}"
            f"{r['accepted']:>11}"
            f"{r['rejected']:>11}"
        )


def main():
    config = load_config(CONFIG_PATH)
    samples = load_samples(config)[:100]

    print(f"Loaded {len(samples)} Visual Genome samples")

    results = benchmark_local(
        config,
        samples,
    )

    for workers in (1, 2, 4):
        results.extend(
            benchmark_ray(
                config,
                samples,
                workers,
            )
        )

    print_summary(results)


if __name__ == "__main__":
    main()