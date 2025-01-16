from pydantic import BaseModel
from tts.voice import Voice


class TtsRequest(BaseModel):
    text: str
    voice: Voice
