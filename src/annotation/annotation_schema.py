from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class AnnotationResult:
    sample_id: str
    image_path: str
    caption: str
    model_name: str
    status: str = "success"
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)