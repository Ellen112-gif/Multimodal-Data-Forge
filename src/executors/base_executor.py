import json
import os


class BaseExecutor:

    def __init__(self):
        self.metrics = {}

    def execute(self, samples):
        raise NotImplementedError

    def print_metrics(self):

        print("\n========== Pipeline Metrics ==========")

        for operator_name, metrics in self.metrics.items():

            print(f"\n{operator_name}")
            print(f"Processed: {metrics['processed']}")
            print(f"Rejected: {metrics['rejected']}")
            print(f"Latency: {metrics['latency']:.4f} s")

        print("\n======================================")

    def save_metrics(self, path):

        directory = os.path.dirname(path)

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.metrics,
                f,
                ensure_ascii=False,
                indent=4
            )