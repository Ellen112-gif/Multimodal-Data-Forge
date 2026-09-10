import ray
from ray.util.actor_pool import ActorPool

from src.executors.base_executor import BaseExecutor
from src.operator_factory import build_operators
from src.pipeline import QualityPipeline


@ray.remote(num_cpus=1)
class PipelineWorker:

    def __init__(self, config):
        operators = build_operators(config)
        self.pipeline = QualityPipeline(operators)

    def ready(self):
        return True

    def process_batch(self, batch):
        return [
            (index, self.pipeline.process(sample))
            for index, sample in batch
        ]

    def get_metrics(self):
        return self.pipeline.metrics


class RayExecutor(BaseExecutor):

    def __init__(
        self,
        config,
        num_workers=2,
        batch_size=2,
        address=None,
    ):
        super().__init__()

        self.config = config
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.address = address

        self.workers = []
        self.pool = None
        self.started_here = False

    def start(self):
        if self.pool is not None:
            return

        self.started_here = not ray.is_initialized()

        if self.started_here:
            if self.address:
                ray.init(
                    address=self.address,
                    ignore_reinit_error=True,
                )
            else:
                ray.init(
                    num_cpus=self.num_workers,
                    object_store_memory=100 * 1024 * 1024,
                    ignore_reinit_error=True,
                )

        self.workers = [
            PipelineWorker.remote(self.config)
            for _ in range(self.num_workers)
        ]

        # Wait until actor initialization and model loading finish.
        ray.get([
            worker.ready.remote()
            for worker in self.workers
        ])

        self.pool = ActorPool(self.workers)

    def execute(self, samples, keep_alive=False):
        if not samples:
            self.metrics = {}
            return []

        if self.pool is None:
            self.start()

        indexed = list(enumerate(samples, start=1))

        batches = [
            indexed[i:i + self.batch_size]
            for i in range(0, len(indexed), self.batch_size)
        ]

        print(
            f"RayExecutor: {len(samples)} samples | "
            f"{len(batches)} batches | "
            f"{self.num_workers} workers | "
            f"batch_size={self.batch_size}"
        )

        batch_results = list(
            self.pool.map(
                lambda worker, batch:
                    worker.process_batch.remote(batch),
                batches,
            )
        )

        results = [
            item
            for batch in batch_results
            for item in batch
        ]

        results.sort(key=lambda item: item[0])

        processed = [
            sample
            for _, sample in results
        ]

        worker_metrics = ray.get([
            worker.get_metrics.remote()
            for worker in self.workers
        ])

        self.metrics = self._merge_metrics(worker_metrics)

        if not keep_alive:
            self.shutdown()

        return processed

    def shutdown(self):
        if self.started_here and ray.is_initialized():
            ray.shutdown()

        self.workers = []
        self.pool = None
        self.started_here = False

    @staticmethod
    def _merge_metrics(worker_metrics):
        merged = {}

        for metrics in worker_metrics:
            for name, values in metrics.items():

                if name not in merged:
                    merged[name] = {
                        "processed": 0,
                        "rejected": 0,
                        "latency": 0.0,
                    }

                merged[name]["processed"] += values["processed"]
                merged[name]["rejected"] += values["rejected"]
                merged[name]["latency"] += values["latency"]

        return merged