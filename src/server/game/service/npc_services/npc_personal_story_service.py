from util.logger import Logger

from game.service.npc_services.npc_database import NpcDatabase
from eventbus.event_producer import EventProducer
from game.data.npc import Npc
from game.data.story_item import StoryItem, StoryItemDataAlias
from game.service.providers.env_provider import EnvProvider
from game.service.story_item.npc_story_item_helper import NpcStoryItemHelper

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
            should_save_behavior = False

            items: list[StoryItem] = []
            for item_data in item_data_list:
                items.append(StoryItem(
                    item_id=npc.personal_story.return_next_item_id_and_inc(),
                    time=self._env_provider.now(),
                    data=item_data
                ))

                if item_data.type == 'change_disposition' and item_data.initiator == npc.actor_ref and item_data.target.type == 'npc':
                    old_relation = npc.behavior.relation_to_other_npc.get(item_data.target.ref_id, 50)
                    new_relation = old_relation + item_data.value
                    new_relation = max(new_relation, 0)
                    new_relation = min(new_relation, 100)

                    npc.behavior.relation_to_other_npc[item_data.target.ref_id] = new_relation
                    should_save_behavior = True

            npc.personal_story.items.extend(items)
            self._db.save_personal_story(npc)

            is_last_item_initiated_by_npc = NpcStoryItemHelper.is_actor_is_initiator(npc.actor_ref, item_data_list[-1])
            if is_last_item_initiated_by_npc:
                should_save_behavior = True

            if should_save_behavior:
                npc.behavior.last_processed_story_item_id = npc.personal_story.items[-1].item_id
                self._db.save_npc_behavior(npc)
