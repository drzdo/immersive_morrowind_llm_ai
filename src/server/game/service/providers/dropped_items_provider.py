from typing import NamedTuple, Sequence
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
from eventbus.rpc import Rpc
from util.logger import Logger

logger = Logger(__name__)


class DroppedItemsProvider:
    class Item(NamedTuple):
        ref_id: str
        object_id: str
        name: str
        dropped_item_id: int

    def __init__(self, consumer: EventConsumer, rpc: Rpc):
        consumer.register_handler(self._handle_event)

        self._rpc = rpc
        self._dropped_items: list[DroppedItemsProvider.Item] = []

    @property
    def dropped_items(self) -> Sequence[Item]:
        return self._dropped_items

    async def _handle_event(self, event: Event):
        if event.data.type == 'item_dropped':
            logger.info(f"Adding dropped item: {event.data}")

            self._dropped_items.append(DroppedItemsProvider.Item(
                ref_id=event.data.ref_id,
                object_id=event.data.object_id,
                name=event.data.name,
                dropped_item_id=event.data.dropped_item_id
            ))
        elif event.data.type == 'activated':
            len_before = len(self._dropped_items)

            target_ref_id = event.data.target_ref_id
            self._dropped_items = list(filter(
                lambda item: item.ref_id != target_ref_id,
                self._dropped_items
            ))

            if len(self._dropped_items) < len_before:
                logger.info(f"Removing dropped item: {event.data}")
