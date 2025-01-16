from pydantic import BaseModel


class TtsResponse(BaseModel):
    file_path: str
    is_pitch_already_applied: bool
