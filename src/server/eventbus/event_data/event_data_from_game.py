from typing import Literal, Optional, Union
from pydantic import BaseModel

from eventbus.data.actor_ref import ActorRef
from eventbus.data.cell import Cell
from eventbus.data.id_with_name import IdWithName

from eventbus.data.crime import CrimeType
from eventbus.data.position import Position
from eventbus.data.topic_data import TopicData


class EventDataFromGame:
    class DialogTextSubmit(BaseModel):
        type: Literal['dialog_text_submit']
        actor_ref: ActorRef
        text: str

    class PlayerStartsSpeakingLookingAt(BaseModel):
        type: Literal['player_starts_speaking_looking_at']
        actor_ref: Optional[ActorRef] = None

    class PlayerStopsSpeakingLookingAt(BaseModel):
        type: Literal['player_stops_speaking_looking_at']
        actor_ref: Optional[ActorRef] = None

    class CellChanged(BaseModel):
        type: Literal['cell_changed']
        cell: Cell

    class ItemDropped(BaseModel):
        type: Literal['item_dropped']
        ref_id: str
        object_id: str
        name: str
        dropped_item_id: int

    class Activated(BaseModel):
        type: Literal['activated']
        activator_actor: ActorRef
        target_actor: Optional[ActorRef] = None
        target_ref_id: str

    class ShowTooltipForRef(BaseModel):
        type: Literal['show_tooltip_for_ref']
        tooltip: Optional[str] = None
        ref_id: str
        object_type: int
        name: Optional[str] = None
        position: Position
        owner: Optional[ActorRef] = None

    class ShowTooltipForInventoryItem(BaseModel):
        type: Literal['show_tooltip_for_inventory_item']
        tooltip: Optional[str] = None
        count: int
        object_type: Optional[int] = None
        name: Optional[str] = None

    class BarterOffer(BaseModel):
        type: Literal['barter_offer']

        # negative means player is buying
        # positive means player is selling
        offer: int
        value: int

        success: bool
        merchant: ActorRef
        buying: list[str]
        selling: list[str]

    class AshfallEatStew(BaseModel):
        type: Literal['ashfall_eat_stew']
        cost: int
        stew_name: str
        in_dialog: bool

    class CrimeWitnessed(BaseModel):
        class VictimFaction(BaseModel):
            faction_id: str
            faction_name: str

        type: Literal['crime_witnessed']
        crime_type: CrimeType
        value: int
        position: tuple[float, float, float]
        witness: ActorRef
        victim_actor: Optional[ActorRef] = None
        victim_faction: Optional[VictimFaction] = None

    class PlayerCollide(BaseModel):
        type: Literal['player_collide']
        other: ActorRef

    class PlayerEquip(BaseModel):
        type: Literal['player_equip']
        item: IdWithName

    class PlayerUnequip(BaseModel):
        type: Literal['player_unequip']
        item: IdWithName

    class NpcMobileActivated(BaseModel):
        type: Literal['npc_mobile_activated']
        actor: ActorRef

    class NpcMobileDeactivated(BaseModel):
        type: Literal['npc_mobile_deactivated']
        actor: ActorRef

    class DialogOpen(BaseModel):
        type: Literal['dialog_open']
        npc_ref: ActorRef
        greet_text: Optional[str] = None
        topics: list[TopicData]

    class DialogUpdate(BaseModel):
        type: Literal['dialog_update']
        npc_ref: ActorRef
        greet_text: Optional[str] = None
        topics: list[TopicData]

    class DialogClose(BaseModel):
        type: Literal['dialog_close']
        npc_ref: ActorRef

    class NpcDeath(BaseModel):
        type: Literal['npc_death']
        actor: ActorRef
        killer: Optional[ActorRef] = None

    class GameLoaded(BaseModel):
        type: Literal['game_loaded']

    class CombatStarted(BaseModel):
        type: Literal['combat_started']
        actor: Optional[ActorRef] = None
        target: Optional[ActorRef] = None

    class CombatStopped(BaseModel):
        type: Literal['combat_stopped']
        actor: Optional[ActorRef] = None

    # NB: Do not forget to add data to the discriminated union to Event.data.


EventDataFromGameUnion = Union[
    EventDataFromGame.DialogTextSubmit,
    EventDataFromGame.PlayerStartsSpeakingLookingAt,
    EventDataFromGame.PlayerStopsSpeakingLookingAt,
    EventDataFromGame.CellChanged,
    EventDataFromGame.ItemDropped,
    EventDataFromGame.Activated,
    EventDataFromGame.ShowTooltipForRef,
    EventDataFromGame.ShowTooltipForInventoryItem,
    EventDataFromGame.BarterOffer,
    EventDataFromGame.AshfallEatStew,
    EventDataFromGame.CrimeWitnessed,
    EventDataFromGame.PlayerCollide,
    EventDataFromGame.PlayerEquip,
    EventDataFromGame.PlayerUnequip,
    EventDataFromGame.NpcMobileActivated,
    EventDataFromGame.NpcMobileDeactivated,
    EventDataFromGame.DialogOpen,
    EventDataFromGame.DialogUpdate,
    EventDataFromGame.DialogClose,
    EventDataFromGame.NpcDeath,
    EventDataFromGame.GameLoaded,
    EventDataFromGame.CombatStarted,
    EventDataFromGame.CombatStopped,
]
