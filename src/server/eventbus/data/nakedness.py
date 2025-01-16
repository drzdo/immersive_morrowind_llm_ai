from pydantic import BaseModel


class Nakedness(BaseModel):
    head: bool
    torso: bool
    feet: bool
    legs: bool
