from typing import Optional

from pydantic import BaseModel

from eventbus.data.actor_ref import ActorRef
from eventbus.data.actor_stats import ActorStats
from eventbus.data.id_with_name import IdWithName
from eventbus.data.nakedness import Nakedness
from eventbus.data.position import Position


class PlayerFactionData(BaseModel):
    faction_id: str
    name: str
    player_joined: bool
    player_expelled: bool
    player_rank: int
    player_reputation: int


class PlayerData(BaseModel):
    ref_id: str
    name: str
    female: bool
    race: IdWithName
    health_normalized: float
    position: Position

    cell: IdWithName

    equipped: list[IdWithName]
    nakedness: Nakedness
    in_dialog: bool

    weapon_drawn: bool
    weapon: Optional[IdWithName] = None

    factions: list[PlayerFactionData]
    gold: int

    stats: ActorStats
    hostiles: list[ActorRef]
