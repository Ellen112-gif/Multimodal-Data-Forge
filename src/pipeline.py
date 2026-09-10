import time
import json
import os

from typing import List

from src.operators.base import BaseOperator
from src.schema.multimodal_sample import MultimodalSample

class QualityPipeline:

    def __init__(self, operators: List[BaseOperator]):
        self.operators = operators

        # Pipeline metrics
        self.metrics = {}

        for operator in operators:

            operator_name = operator.__class__.__name__

            self.metrics[operator_name] = {
                "processed": 0,
                "rejected": 0,
                "latency": 0.0,
            }

    def process(self, sample: MultimodalSample) -> MultimodalSample:

        for operator in self.operators:

            # 如果已经被前面的 Operator 拒绝，
            # 后面的 Operator 不再运行
            if sample.status == "rejected":
                break

            operator_name = (operator.__class__.__name__)

            # 记录执行前状态
            previous_status = sample.status

            # 开始计时
            start_time = time.perf_counter()

            # 执行 Operator
            sample = operator.process(sample)

            # 结束计时
            elapsed_time = (
                time.perf_counter()
                - start_time
            )

            # processed + 1
            self.metrics[
                operator_name
            ]["processed"] += 1

            # latency 累积
            self.metrics[
                operator_name
            ]["latency"] += elapsed_time

            # 如果这个 Operator
            # 把 accepted 变成 rejected
            if (
                previous_status != "rejected"
                and sample.status == "rejected"
            ):
                self.metrics[
                    operator_name
                ]["rejected"] += 1

        return sample

    def run(
        self,
        samples: List[MultimodalSample]) -> List[MultimodalSample]:

        results = []

        for sample in samples:

            processed_sample = (
                self.process(sample)
            )

            results.append(
                processed_sample
            )

        return results

    def print_metrics(self):

        print(
            "\n========== Pipeline Metrics =========="
        )

        for operator_name, metrics in self.metrics.items():

            print(f"\n{operator_name}")

            print(
                f"Processed: "
                f"{metrics['processed']}"
            )

            print(
                f"Rejected: "
                f"{metrics['rejected']}"
            )

            print(
                f"Latency: "
                f"{metrics['latency']:.4f} s"
            )

        print(
            "\n======================================"
        )
    def save_metrics(self, path: str):

        os.makedirs( os.path.dirname(path), exist_ok=True)

        with open(path,"w",encoding="utf-8") as f:

            json.dump(self.metrics, f, ensure_ascii=False, indent=4 )