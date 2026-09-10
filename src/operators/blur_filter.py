import cv2
from src.schema.multimodal_sample import MultimodalSample
from src.operators.base import BaseOperator
class BlurFilter(BaseOperator):
    def __init__(self, threshold=100.0):
        self.threshold= threshold
    
    def process(self, sample:MultimodalSample) -> MultimodalSample:
        if sample.status == "rejected":
            return sample
        if not sample.image_path:
            sample.status = "rejected"
            sample.reject_reason = "missing_image_path"
            return sample
        
        image = cv2.imread(sample.image_path)
        
        if image is None:
            sample.status = "rejected"
            sample.reject_reason = "invalid_image"
            return sample   
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        sample.blur_score = float(blur_score)
        
        if blur_score < self.threshold:
            sample.status = "rejected"
            sample.reject_reason = "blurry_image"
            return sample

        sample.status = "accepted"
        sample.reject_reason = None

        return sample