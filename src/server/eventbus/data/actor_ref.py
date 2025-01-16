from typing import Literal, Union

from pydantic import BaseModel


class ActorRef(BaseModel):
    ref_id: str
    type: Union[Literal['player'], Literal['npc'], Literal['creature']]
    name: str
    female: bool

    def __str__(self) -> str:
        return self.ref_id

    def __hash__(self) -> int:
        return self.ref_id.__hash__()
