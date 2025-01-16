from pydantic import BaseModel
from tts.voice import Voice


class NpcPersonality(BaseModel):
    background: str
    voice: Voice
