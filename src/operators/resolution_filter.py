from src.schema.multimodal_sample import MultimodalSample
from src.operators.base import BaseOperator

class ResolutionFilter(BaseOperator):
    def __init__(self, min_width=512, min_height=512):
        self.min_width = min_width
        self.min_height = min_height
    
    def process(self, sample:MultimodalSample) -> MultimodalSample:
        if sample.status == "rejected":
            return sample
        
        if sample.width is None or sample.height is None:
            sample.status = "rejected"
            sample.reject_reason = "missing_resolution"
            return sample
        if (sample.width < self.min_width
            or sample.height < self.min_height):
            sample.status = "rejected"
            sample.reject_reason = "low_resolution"
            return sample
        return sample
        