import datetime
from pathvalidate import sanitize_filename
from pydantic import BaseModel
from database.database import Database
from eventbus.data.npc_data import NpcData
from game.data.npc import Npc
from game.data.npc_behavior import NpcBehavior
from game.data.npc_personality import NpcPersonality
from game.data.story import Story
from game.data.story_item import StoryItem
from game.data.time import Time
from util.logger import Logger

logger = Logger(__name__)


class NpcDatabase:
    class Config(BaseModel):
        max_stored_story_items: int
        max_used_in_llm_story_items: int

    def __init__(self, config: Config, db: Database):
        self._config = config
        self._db = db

    #
    def save_personal_story(self, npc: Npc):
        self._save_personal_story(npc.actor_ref.ref_id, npc.personal_story, "personal_story")

    def _save_personal_story(self, npc_ref_id: str, story: Story, file_name: str):
        if len(story.items) > self._config.max_stored_story_items:
            story.items = story.items[-self._config.max_stored_story_items:]

        self._db.save_model(
            path=['npc', npc_ref_id, file_name],
            value=story
        )

    def load_personal_story(self, npc_ref_id: str, time: Time) -> Story | None:
        story = self._db.load_model(
            type=Story,
            path=['npc', npc_ref_id, 'personal_story']
        )

        should_rewind_story = True  # TODO: add toggle
        if story and should_rewind_story:
            items_happened_before: list[StoryItem] = []
            items_happened_later: list[StoryItem] = []
            for item in story.items:
                if item.time.game_time <= time.game_time:
                    items_happened_before.append(item)
                else:
                    items_happened_later.append(item)

            if len(items_happened_later) > 0:
                backup_filename = sanitize_filename(f"personal_story_backup_{datetime.datetime.now().isoformat()}")
                logger.warning(
                    f"Personal story of {npc_ref_id} has {len(items_happened_later)} items happened after {time.game_time}, going to back it up to {backup_filename} and remove from the original story")

                self._save_personal_story(npc_ref_id, story, backup_filename)
                story.items = items_happened_before

                self._save_personal_story(npc_ref_id, story, "personal_story")

        return story

    #
    def save_npc_data(self, npc: Npc):
        self._db.save_model(
            path=['npc', npc.actor_ref.ref_id, 'last_npc_data'],
            value=npc.npc_data
        )

    def load_npc_data(self, npc_ref_id: str, time: Time) -> NpcData | None:
        return self._db.load_model(
            type=NpcData,
            path=['npc', npc_ref_id, 'last_npc_data']
        )

    #
    def save_npc_behavior(self, npc: Npc):
        self._db.save_model(
            path=['npc', npc.actor_ref.ref_id, 'behavior'],
            value=npc.behavior
        )

    def load_npc_behavior(self, npc_ref_id: str, time: Time) -> NpcBehavior | None:
        return self._db.load_model(
            type=NpcBehavior,
            path=['npc', npc_ref_id, 'behavior']
        )

    #
    def save_npc_personality(self, npc: Npc):
        # self._db.save_text(
        #     path=['npc', npc.actor_ref.ref_id, 'background'],
        #     text=npc.personality.background
        # )
        self._db.save_model(
            path=['npc', npc.actor_ref.ref_id, 'personality'],
            value=npc.personality
        )

    def load_npc_personality(self, npc_ref_id: str, time: Time) -> NpcPersonality | None:
        # bg = self._db.load_text(
        #     path=['npc', npc_ref_id, 'background']
        # )
        # if bg is None:
        #     return None

        personality = self._db.load_model(
            type=NpcPersonality,
            path=['npc', npc_ref_id, 'personality']
        )
        # if personality is None:
        #     return None

        # personality.background = bg
        return personality
