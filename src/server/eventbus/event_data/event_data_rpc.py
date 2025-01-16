from typing import Literal, Optional, Union
from pydantic import BaseModel

from eventbus.data.npc_data import NpcData
from eventbus.data.player_data import PlayerData
from eventbus.data.actor_ref import ActorRef
from eventbus.data.env_data import EnvData
from eventbus.data.player_data_fast import PlayerDataFast


class EventDataRpc:
    #
    class GetLocalPlayerRequest(BaseModel):
        type: Literal['get_local_player_request']

    class GetLocalPlayerResponse(BaseModel):
        type: Literal['get_local_player_response']
        player_data: PlayerData

    #
    class GetLocalPlayerFastRequest(BaseModel):
        type: Literal['get_local_player_fast_request']

    class GetLocalPlayerFastResponse(BaseModel):
        type: Literal['get_local_player_fast_response']
        player_data_fast: PlayerDataFast

    #
    class GetNpcRequest(BaseModel):
        type: Literal['get_npc_request']
        npc_ref_id: str

    class GetNpcResponse(BaseModel):
        type: Literal['get_npc_response']
        npc_data: NpcData

    #
    class GetActorsNearbyRequest(BaseModel):
        type: Literal['get_actors_nearby_request']
        actor_ref_id: Optional[str]
        radius_ingame: Optional[float]
        test_line_of_sight: Optional[bool]

    class GetActorsNearbyResponse(BaseModel):
        class ActorNearby(BaseModel):
            actor_ref: ActorRef
            distance_ingame: float
            can_see: Optional[bool] = None

        type: Literal['get_actors_nearby_response']
        actors: list[ActorNearby]

    #
    class GetEnvRequest(BaseModel):
        type: Literal['get_env_request']

    class GetEnvResponse(BaseModel):
        type: Literal['get_env_response']
        env_data: EnvData

    #
    class GetItemCountRequest(BaseModel):
        type: Literal['get_item_count_request']
        ref_id: str
        item: str

    class GetItemCountResponse(BaseModel):
        type: Literal['get_item_count_response']
        count: int

    #
    class LineOfSightRequest(BaseModel):
        type: Literal['line_of_sight_request']
        npc_ref_id: str

    class LineOfSightResponse(BaseModel):
        type: Literal['line_of_sight_response']
        can_see: bool

    #
    class IsRefValidRequest(BaseModel):
        type: Literal['is_ref_valid_request']
        ref_id: str

    class IsRefValidResponse(BaseModel):
        type: Literal['is_ref_valid_response']
        is_valid: bool

    # NB: Do not forget to add data to the discriminated union below.


EventDataRpcUnion = Union[
    EventDataRpc.GetLocalPlayerRequest,
    EventDataRpc.GetLocalPlayerResponse,

    EventDataRpc.GetLocalPlayerFastRequest,
    EventDataRpc.GetLocalPlayerFastResponse,

    EventDataRpc.GetNpcRequest,
    EventDataRpc.GetNpcResponse,

    EventDataRpc.GetActorsNearbyRequest,
    EventDataRpc.GetActorsNearbyResponse,

    EventDataRpc.GetEnvRequest,
    EventDataRpc.GetEnvResponse,

    EventDataRpc.GetItemCountRequest,
    EventDataRpc.GetItemCountResponse,

    EventDataRpc.LineOfSightRequest,
    EventDataRpc.LineOfSightResponse,

    EventDataRpc.IsRefValidRequest,
    EventDataRpc.IsRefValidResponse,
]
