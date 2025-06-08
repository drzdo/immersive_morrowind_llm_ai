from typing import Literal, Optional, TypeAlias, Union

from eventbus.data.cell import Cell
from eventbus.data.position import Position
from game.data.time import Time

from pydantic import BaseModel, Field

from eventbus.data.actor_ref import ActorRef


class StoryItemData:
    class SayRaw(BaseModel):
        type: Literal['say_raw']
        speaker: ActorRef
        target: Optional[ActorRef]
        text: str

    class SayProcessed(BaseModel):
        type: Literal['say_processed']
        speaker: ActorRef
        target: Optional[ActorRef]
        text: str
        audio_duration_sec: Optional[float] = None

    class PlayerTriggerDialogTopic(BaseModel):
        type: Literal['player_trigger_dialog_topic']
        speaker: ActorRef
        target: ActorRef
        original_text: str
        trigger_topic: str
        # topic_text: str

    class NpcTriggerDialogTopic(BaseModel):
        type: Literal['npc_trigger_dialog_topic']
        speaker: ActorRef
        target: ActorRef
        topic_name: str
        topic_response: str

    class PlayerTriggerListDialogTopics(BaseModel):
        type: Literal['player_trigger_list_dialog_topics']
        speaker: ActorRef
        target: ActorRef
        original_text: str

    class ChangeDisposition(BaseModel):
        type: Literal['change_disposition']
        initiator: ActorRef
        target: ActorRef
        value: int
        reasons: list[str]

    class NpcStartFollow(BaseModel):
        type: Literal['npc_start_follow']
        initiator: ActorRef
        target: ActorRef
        duration_hours: Optional[float]

    class NpcStopFollow(BaseModel):
        type: Literal['npc_stop_follow']
        initiator: ActorRef
        target: ActorRef

    class NpcPickUpItem(BaseModel):
        type: Literal['npc_pick_up_item']
        initiator: ActorRef
        item_ref_id: str
        item_name: str
        dropped_item_id: Optional[int] = Field(default=None)

    class NpcAttack(BaseModel):
        type: Literal['npc_attack']
        initiator: ActorRef
        victim: ActorRef

    class NpcCome(BaseModel):
        type: Literal['npc_come']
        initiator: ActorRef
        target: ActorRef

    class NpcActivate(BaseModel):
        type: Literal['npc_activate']
        initiator: ActorRef
        target_ref_id: str
        target_position: list[float]

    class NpcTravel(BaseModel):
        type: Literal['npc_travel']
        initiator: ActorRef
        destination: list[float]

    class NpcDeath(BaseModel):
        type: Literal['npc_death']
        victim: ActorRef
        killer: Optional[ActorRef] = None

    class AshfallEatStew(BaseModel):
        type: Literal['ashfall_eat_stew']
        initiator: ActorRef
        seller: ActorRef
        stew_name: str
        cost: int

    class BarterOffer(BaseModel):
        type: Literal['barter_offer']

        # negative means player is buying
        # positive means player is selling
        offer: int
        value: int

        success: bool
        buyer: ActorRef
        merchant: ActorRef
        buying: list[str]
        selling: list[str]

    class ActorPickReason(BaseModel):
        type: Literal['actor_pick_reason']
        actor: ActorRef
        reason: str

    class NpcDropItem(BaseModel):
        type: Literal['npc_drop_item']
        initiator: ActorRef
        item_id: str
        item_name: str
        count: int
        water_amount: Optional[int]

    class PlayerCellChanged(BaseModel):
        type: Literal['player_cell_changed']
        initiator: ActorRef
        cell: Cell

    class PlayerTellsToShutUp(BaseModel):
        type: Literal['player_tells_to_shut_up']
        speaker: ActorRef

    class PlayerTellsToStopCombat(BaseModel):
        type: Literal['player_tells_to_stop_combat']
        speaker: ActorRef

    class PlayerTriggerSheogorathLevel(BaseModel):
        type: Literal['player_trigger_sheogorath_level']
        speaker: ActorRef
        sheogorath_level: Literal['normal', 'mad']

    class PlayerPointsAtRef(BaseModel):
        type: Literal['player_points_at_ref']
        speaker: ActorRef

        target_ref_id: str
        target_name: str
        target_owner: Optional[ActorRef]
        target_position: Position

    # NB: do not forget to add class name to the union below.


StoryItemDataAlias: TypeAlias = Union[
    StoryItemData.SayRaw,
    StoryItemData.SayProcessed,
    StoryItemData.PlayerTriggerDialogTopic,
    StoryItemData.NpcTriggerDialogTopic,
    StoryItemData.PlayerTriggerListDialogTopics,
    StoryItemData.ChangeDisposition,
    StoryItemData.NpcStartFollow,
    StoryItemData.NpcStopFollow,
    StoryItemData.NpcActivate,
    StoryItemData.NpcTravel,
    StoryItemData.NpcPickUpItem,
    StoryItemData.NpcAttack,
    StoryItemData.NpcCome,
    StoryItemData.NpcDeath,
    StoryItemData.AshfallEatStew,
    StoryItemData.BarterOffer,
    StoryItemData.ActorPickReason,
    StoryItemData.NpcDropItem,
    StoryItemData.PlayerCellChanged,
    StoryItemData.PlayerTellsToShutUp,
    StoryItemData.PlayerTellsToStopCombat,
    StoryItemData.PlayerTriggerSheogorathLevel,
    StoryItemData.PlayerPointsAtRef,
]


class StoryItem(BaseModel):
    item_id: int
    time: Time

    data: StoryItemDataAlias = Field(discriminator='type')
