from typing import Literal, Optional, Union
from pydantic import BaseModel

from eventbus.data.crime import CrimeType
from eventbus.data.actor_ref import ActorRef


class EventDataFromServer:
    class SttStartListening(BaseModel):
        type: Literal['stt_start_listening']

    class SttStopListening(BaseModel):
        type: Literal['stt_stop_listening']

    class SttRecognitionUpdate(BaseModel):
        type: Literal['stt_recognition_update']
        text: str

    class SttRecognitionComplete(BaseModel):
        type: Literal['stt_recognition_complete']
        text: str

    class ActorSays(BaseModel):
        type: Literal['actor_says']
        speaker_ref: ActorRef
        target_ref: ActorRef | None
        text: str
        audio_duration_sec: Optional[float]
        reaction_text: Optional[str]

    class NpcSayMp3(BaseModel):
        type: Literal['npc_say_mp3']
        npc_ref_id: str
        file_path: str
        pitch: float
        target_ref_id: Optional[str]
        duration_sec: float

    class NpcRemoveSound(BaseModel):
        type: Literal['npc_remove_sound']
        npc_ref_id: str

    class NpcStartCombat(BaseModel):
        type: Literal['npc_start_combat']
        npc_ref_id: str
        target_ref_id: str

    class NpcStopCombat(BaseModel):
        type: Literal['npc_stop_combat']
        npc_ref_id: str

    class NpcFollow(BaseModel):
        type: Literal['npc_follow']
        npc_ref_id: str
        target_ref_id: str
        duration_hours: Optional[float]

    class NpcWander(BaseModel):
        type: Literal['npc_wander']
        npc_ref_id: str
        range: Optional[float]

    class TriggerCrime(BaseModel):
        type: Literal['trigger_crime']
        crime_value: int
        crime_type: CrimeType

    class TransferItem(BaseModel):
        type: Literal['transfer_item']
        from_ref_id: str
        to_ref_id: str
        item: str
        count: int

    class NpcSetPitch(BaseModel):
        type: Literal['npc_set_pitch']
        npc_ref_id: str
        pitch: float

    class ChangeDisposition(BaseModel):
        type: Literal['change_disposition']
        npc_ref_id: str
        value: int

    class TriggerTopicInDialog(BaseModel):
        type: Literal['trigger_topic_in_dialog']
        topic: str

    class NpcActivate(BaseModel):
        type: Literal['npc_activate']
        npc_ref_id: str
        target_ref_id: str
        dropped_item_id: Optional[int]

    class NpcDropItem(BaseModel):
        type: Literal['npc_drop_item']
        npc_ref_id: str
        item: str
        count: int

    class NpcSpawnItem(BaseModel):
        type: Literal['npc_spawn_item']
        npc_ref_id: str
        item: str
        count: int
        water_amount: Optional[int]

    class NpcTravel(BaseModel):
        type: Literal['npc_travel']
        npc_ref_id: str
        target_ref_id: str

    class TurnActorsTo(BaseModel):
        type: Literal['turn_actors_to']
        actor_ref_ids: list[str]
        target_ref_id: str

    class UpdatePlayerBook(BaseModel):
        type: Literal['update_player_book']
        player_book_name: str
        player_book_content: str

    # NB: Do not forget to add data to the discriminated union to Event.data.


EventDataFromServerUnion = Union[
    EventDataFromServer.SttStartListening,
    EventDataFromServer.SttStopListening,
    EventDataFromServer.SttRecognitionUpdate,
    EventDataFromServer.SttRecognitionComplete,
    EventDataFromServer.ActorSays,
    EventDataFromServer.NpcSayMp3,
    EventDataFromServer.NpcRemoveSound,
    EventDataFromServer.NpcStartCombat,
    EventDataFromServer.NpcStopCombat,
    EventDataFromServer.NpcFollow,
    EventDataFromServer.ChangeDisposition,
    EventDataFromServer.NpcWander,
    EventDataFromServer.TriggerCrime,
    EventDataFromServer.TransferItem,
    EventDataFromServer.NpcSetPitch,
    EventDataFromServer.TriggerTopicInDialog,
    EventDataFromServer.NpcActivate,
    EventDataFromServer.NpcDropItem,
    EventDataFromServer.NpcSpawnItem,
    EventDataFromServer.NpcTravel,
    EventDataFromServer.TurnActorsTo,
    EventDataFromServer.UpdatePlayerBook,
]
