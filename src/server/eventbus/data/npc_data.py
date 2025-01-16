from typing import Optional

from pydantic import BaseModel

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

    travel_destinations: Optional[list[str]] = None


class NpcFactionData(BaseModel):
    faction_id: str
    faction_name: str
    npc_rank: int


class NpcCellData(BaseModel):
    id: str
    name: Optional[str] = None


class NpcData(BaseModel):
    ref_id: str
    name: str
    has_mobile: bool

    female: bool
    class_id: Optional[str] = None
    class_name: Optional[str] = None

    cell: NpcCellData
    npc_in_active_cell: bool

    player_distance: float
    disposition: int

    is_diseased: bool
    in_combat: bool
    is_dead: bool

    is_ashfall_innkeeper: bool
    ashfall_stew_cost: Optional[int] = None

    friendlies: list[ActorRef]
    hostiles: list[ActorRef]

    equipped: list[IdWithName]
    nakedness: Nakedness

    health_normalized: float
    race: IdWithName

    weapon_drawn: bool
    weapon: Optional[IdWithName] = None

    following: Optional[ActorRef] = None
    position: Position
    ai_config: NpcAiConfig

    faction: Optional[NpcFactionData] = None
    stats: ActorStats
    gold: int
