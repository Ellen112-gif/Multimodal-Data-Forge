from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class MultimodalSample:
    sample_id: str

    character: str
    scene: str

    dialogue: str
    image_prompt: str

    emotion: str
    action: str
    visual_style: str

    image_path: Optional[str] = None

    width: Optional[int] = None
    height: Optional[int] = None

    blur_score: Optional[float] = None
    clip_score: Optional[float] = None

    status: str = "pending"
    reject_reason: Optional[str] = None

    def to_dict(self):
        return asdict(self)