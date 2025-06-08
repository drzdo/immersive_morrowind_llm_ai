from typing import Literal, Optional
from pydantic import BaseModel, Field


class Voice(BaseModel):
    class Elevenlabs(BaseModel):
        stability: float = Field(default=0.9)
        similarity_boost: float = Field(default=0.5)
        style: float = Field(default=0.5)
        use_speaker_boost: bool = Field(default=True)

    speaker_ref_id: Optional[str] = None
    race_id: Optional[str] = None
    female: bool
    pitch: float = Field(default=1.0)
    accent: Literal['none', 'translit', 'ashkhan']

    elevenlabs: Elevenlabs
