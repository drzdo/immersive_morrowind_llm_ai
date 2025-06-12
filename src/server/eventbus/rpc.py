import asyncio
from eventbus.data.player_data_fast import PlayerDataFast
from util.logger import Logger
import time

from pydantic import BaseModel
from eventbus.bus import EventBus
from eventbus.event import Event
from eventbus.event_data.event_data_rpc import EventDataRpc
from eventbus.data.env_data import EnvData
from eventbus.data.npc_data import NpcData
from eventbus.data.player_data import PlayerData

logger = Logger(__name__)

class Rpc:
    class Config(BaseModel):
        max_wait_time_sec: float

    def __init__(self, config: Config, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._event_bus.register_handler(self._handle_event)

        self._waiting_response_for_event_ids: set[int] = set()
        self._request_event_id_to_response_event: dict[int, Event] = {}

    async def get_npc_data(self, npc_ref_id: str) -> NpcData:
        request = Event(data=EventDataRpc.GetNpcRequest(
            type='get_npc_request',
            npc_ref_id=npc_ref_id
        ))

        response = await self._call(request)
        if response.data.type != 'get_npc_response':
            self._raise_unknown_response_exception(request, response)
        return response.data.npc_data

    async def get_local_player(self) -> PlayerData:
        request = Event(data=EventDataRpc.GetLocalPlayerRequest(type='get_local_player_request'))
        response = await self._call(request)
        if response.data.type != 'get_local_player_response':
            self._raise_unknown_response_exception(request, response)
        return response.data.player_data

    async def get_local_player_fast(self) -> PlayerDataFast:
        request = Event(data=EventDataRpc.GetLocalPlayerFastRequest(type='get_local_player_fast_request'))
        response = await self._call(request)
        if response.data.type != 'get_local_player_fast_response':
            self._raise_unknown_response_exception(request, response)
        return response.data.player_data_fast

    async def get_env(self) -> EnvData:
        request = Event(data=EventDataRpc.GetEnvRequest(type='get_env_request'))
        response = await self._call(request)
        if response.data.type != 'get_env_response':
            self._raise_unknown_response_exception(request, response)
        return response.data.env_data

    async def get_actors_nearby(self, data: EventDataRpc.GetActorsNearbyRequest) -> EventDataRpc.GetActorsNearbyResponse:
        request = Event(data=data)
        response = await self._call(request)
        if response.data.type != 'get_actors_nearby_response':
            self._raise_unknown_response_exception(request, response)
        return response.data

    async def _call(self, request_event: Event) -> Event:
        # event_id is set only after this call.
        self._event_bus.produce_event(request_event)

        self._waiting_response_for_event_ids.add(request_event.event_id)
        logger.debug(f"RPC call added id={request_event.event_id} total={len(self._waiting_response_for_event_ids)}")

        t0 = time.time()
        while True:
            if (time.time() - t0) > self._config.max_wait_time_sec:
                self._raise_timeout_exception(request_event)

            if request_event.event_id not in self._request_event_id_to_response_event:
                await asyncio.sleep(1.0 / 20.0)
                continue

            response_event = self._request_event_id_to_response_event.pop(request_event.event_id)
            logger.debug(f"RPC call resolved id={request_event.event_id} in {time.time() - t0} sec")

            return response_event

    async def _handle_event(self, event: Event):
        if event.response_to_event_id is None:
            return

        if event.response_to_event_id in self._waiting_response_for_event_ids:
            self._waiting_response_for_event_ids.remove(event.response_to_event_id)
            self._request_event_id_to_response_event[event.response_to_event_id] = event

            logger.debug(f"Received response event for id={event.response_to_event_id}")
        else:
            logger.error(f"Received unexpected response event: {event}")

    def _raise_unknown_response_exception(self, request: Event, response: Event):
        logger.error(f"Received unexpected response: request={request} response={response}")
        raise Exception("Received unexpected response")

    def _raise_timeout_exception(self, request: Event):
        logger.error(f"RPC call timeout: request={request}")
        raise Exception("RPC call timeout")
