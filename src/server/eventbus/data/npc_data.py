from typing import Optional

from pydantic import BaseModel, Field

from eventbus.data.actor_ref import ActorRef
from eventbus.data.actor_stats import ActorStats
from eventbus.data.id_with_name import IdWithName
from eventbus.data.nakedness import Nakedness
from eventbus.data.position import Position


class NpcAiConfig(BaseModel):
    offers_bartering: bool
    offers_spellmaking: bool
    offers_spells: bool
    offers_training: bool
    offers_enchanting: bool
    offers_repairs: bool

    barters_misc_items: bool
    barters_lights: bool
    barters_apparatus: bool
    barters_ingredients: bool
    barters_weapons: bool
    barters_repair_tools: bool
    barters_lockpicks: bool
    barters_probes: bool
    barters_clothing: bool
    barters_alchemy: bool
    barters_armor: bool
    barters_books: bool
    barters_enchanted_items: bool

    travel_destinations: Optional[list[str]] = Field(default=None)


class NpcFactionData(BaseModel):
    faction_id: str
    faction_name: str
    npc_rank: int


class NpcCellData(BaseModel):
    id: str
    name: Optional[str] = Field(default=None)


class NpcData(BaseModel):
    ref_id: str
    name: str
    has_mobile: bool

    female: bool = Field(default=False)
    class_id: Optional[str] = Field(default=None)
    class_name: Optional[str] = Field(default=None)

    cell: NpcCellData
    npc_in_active_cell: bool

    player_distance: float
    disposition: int = Field(default=50)

    is_diseased: bool
    in_combat: bool
    is_dead: bool

    is_ashfall_innkeeper: bool
    ashfall_stew_cost: Optional[int] = Field(default=None)

    friendlies: list[ActorRef]
    hostiles: list[ActorRef]

    equipped: list[IdWithName]
    nakedness: Nakedness

    health_normalized: float
    race: Optional[IdWithName] = Field(default=None)

    weapon_drawn: bool
    weapon: Optional[IdWithName] = Field(default=None)

    following: Optional[ActorRef] = Field(default=None)
    position: Position
    ai_config: NpcAiConfig

    faction: Optional[NpcFactionData] = Field(default=None)
    stats: Optional[ActorStats] = Field(default=None)
    gold: int
