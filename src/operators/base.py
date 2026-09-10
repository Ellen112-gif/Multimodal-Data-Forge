from abc import ABC, abstractmethod
from src.schema.multimodal_sample import MultimodalSample

class BaseOperator(ABC):
    @abstractmethod
    def process(self, sample:MultimodalSample) -> MultimodalSample:
        pass