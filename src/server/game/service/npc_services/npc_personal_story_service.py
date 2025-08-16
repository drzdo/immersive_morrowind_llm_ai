from util.logger import Logger

from game.service.npc_services.npc_database import NpcDatabase
from eventbus.event_producer import EventProducer
from game.data.npc import Npc
from game.data.story_item import StoryItem, StoryItemDataAlias
from game.service.providers.env_provider import EnvProvider

logger = Logger(__name__)


class NpcPersonalStoryService:
    def __init__(self, db: NpcDatabase, env_provider: EnvProvider, producer: EventProducer) -> None:
        self._db = db
        self._env_provider = env_provider
        self._producer = producer

    def add_items_to_personal_stories(
        self,
        npcs: list[Npc],
        item_data_list: list[StoryItemDataAlias]
    ):
        if len(item_data_list) == 0:
            return

        for npc in npcs:
            items: list[StoryItem] = []
            for item_data in item_data_list:
                items.append(StoryItem(
                    item_id=npc.personal_story.return_next_item_id_and_inc(),
                    time=self._env_provider.now(),
                    data=item_data
                ))

            npc.personal_story.items.extend(items)
            self._db.save_npc(npc)
