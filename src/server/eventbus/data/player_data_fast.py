from typing import Optional
from pydantic import BaseModel

from eventbus.data.id_with_name import IdWithName
from eventbus.data.position import Position


class PlayerDataFast(BaseModel):
    health_normalized: float
    position: Position
    cell: IdWithName
    in_dialog: bool

    weapon_drawn: bool
    weapon: Optional[IdWithName] = None
    gold: int
