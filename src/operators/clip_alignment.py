import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from src.schema.multimodal_sample import MultimodalSample
from src.operators.base import BaseOperator

class CLIPAlignmentOperator(BaseOperator):
    def __init__(self, model_name="openai/clip-vit-base-patch32", threshold=0.20):
        self.threshold = threshold
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"CLIP device: {self.device}")

        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

    def process(self, sample: MultimodalSample) -> MultimodalSample:
        if sample.status == "rejected":
            return sample
        if not sample.image_prompt:
            sample.status = "rejected"
            sample.reject_reason = "missing_image_prompt"
            return sample

        image = Image.open(sample.image_path).convert("RGB")
        
        inputs = self.processor(
            text=[sample.image_prompt],
            images=image,
            return_tensors="pt",
            padding=True
        )

        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            image_features = self.model.get_image_features(pixel_values=inputs["pixel_values"])
            text_features = self.model.get_text_features(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )

        # L2 normalization
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarity = (image_features @ text_features.T).item()
        sample.clip_score = float(similarity)

        if similarity < self.threshold:
            sample.status = "rejected"
            sample.reject_reason = "low_clip_alignment"
            return sample
        sample.status = "accepted"
        sample.reject_reason = None
        return sample