from src.executors.base_executor import BaseExecutor
from src.operator_factory import build_operators
from src.pipeline import QualityPipeline


class LocalExecutor(BaseExecutor):

    def __init__(self, config):
        super().__init__()

        operators = build_operators(config)
        self.pipeline = QualityPipeline(operators)

    def execute(self, samples):
        processed = [
            self.pipeline.process(sample)
            for sample in samples
        ]

        self.metrics = self.pipeline.metrics
        return processed