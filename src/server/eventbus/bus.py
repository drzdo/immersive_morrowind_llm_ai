import asyncio
from util.logger import Logger
import traceback
from typing import Any, Callable, Coroutine, List, Literal

from pydantic import BaseModel
from eventbus.backend.abstract import AbstractEventBusBackend
from eventbus.backend.mwse_tcp import MwseTcpEventBusBackend
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
from eventbus.event_producer import EventProducer

logger = Logger(__name__)


class EventBus(EventProducer, EventConsumer):
    class Config(BaseModel):
        class MwseTcp(BaseModel):
            type: Literal['mwse_tcp']
            mwse_tcp: MwseTcpEventBusBackend.Config

        system: MwseTcp
        producers: int
        consumers: int

    def __init__(self, config: Config):
        self._config = config

        self._next_event_id = 1

        self._backend = self._create_backend()
        self._handlers: List[Callable[[Event], Coroutine[Any, Any, None]]] = []

        self._events_to_produce_to_game: list[Event] = []
        self._events_consumed_from_game: list[Event] = []

    def start(self):
        for _ in range(0, self._config.producers):
            asyncio.get_event_loop().create_task(self._producer())

        for _ in range(0, self._config.consumers):
            asyncio.get_event_loop().create_task(self._consumer())

        self._backend.start(self._handle_event_from_game)

    def is_connected_to_game(self):
        return self._backend.is_connected_to_game()

    def _create_backend(self) -> AbstractEventBusBackend:
        return MwseTcpEventBusBackend(self._config.system.mwse_tcp)

    async def _consumer(self):
        while True:
            processed = False

            if len(self._events_consumed_from_game) > 0:
                processed = True
                event = self._events_consumed_from_game.pop(0)
                Logger.set_ctx(f"consumer_event:{event.event_id}")

                for h in self._handlers:
                    try:
                        await h(event)
                    except Exception as error:
                        logger.error(f"Consumer handler failed: event={event} error={error}")
                        logger.debug(traceback.format_exc())

            if not processed:
                await asyncio.sleep(1.0 / 30.0)

    async def _producer(self):
        while True:
            processed = False

            if len(self._events_to_produce_to_game) > 0:
                processed = True
                event = self._events_to_produce_to_game.pop(0)
                Logger.set_ctx(f"produce_event:{event.event_id}")

                self._backend.publish_event_to_game(event)

                for h in self._handlers:
                    try:
                        await h(event)
                    except Exception as error:
                        logger.error(f"Handler failed: event={event} error={error}")
                        logger.debug(traceback.format_exc())

            if not processed:
                await asyncio.sleep(1.0 / 30.0)

    def _handle_event_from_game(self, event: Event):
        logger.debug(f"> from game: {event}")
        self._events_consumed_from_game.append(event)

    def register_handler(self, handler: Callable[[Event], Coroutine[Any, Any, None]]):
        self._handlers.append(handler)

    def produce_event(self, event: Event):
        event.event_id = self._next_event_id
        self._next_event_id = self._next_event_id + 1

        logger.debug(f"> to game: {event}")
        self._events_to_produce_to_game.append(event)
