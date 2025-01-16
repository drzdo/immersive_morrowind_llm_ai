from pydantic import BaseModel


class IdWithName(BaseModel):
    id: str
    name: str
