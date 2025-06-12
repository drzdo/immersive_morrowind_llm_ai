import datetime
from pathvalidate import sanitize_filename
from pydantic import BaseModel
from database.database import Database
from game.data.player import Player
from game.data.story import Story
from game.data.story_item import StoryItem
from game.data.time import Time
from util.logger import Logger

logger = Logger(__name__)


class PlayerDatabase:
    class Config(BaseModel):
        max_stored_story_items: int
        max_shown_story_items: int
        book_name: str

    def __init__(self, config: Config, db: Database):
        self.config = config
        self._db = db

    #
    def save_personal_story(self, player: Player):
        self._save_personal_story(player.actor_ref.ref_id, player.personal_story, "personal_story")

    def _save_personal_story(self, ref_id: str, story: Story, file_name: str):
        if len(story.items) > self.config.max_stored_story_items:
            story.items = story.items[-self.config.max_stored_story_items:]

        self._db.save_model(
            path=['player', ref_id, file_name],
            value=story
        )

    def load_personal_story(self, ref_id: str, time: Time) -> Story | None:
        story = self._db.load_model(
            type=Story,
            path=['player', ref_id, 'personal_story']
        )

        if story:
            items_happened_before: list[StoryItem] = []
            items_happened_later: list[StoryItem] = []
            for item in story.items:
                if item.time.game_time <= time.game_time:
                    items_happened_before.append(item)
                else:
                    items_happened_later.append(item)

            if items_happened_later:
                backup_filename = sanitize_filename(f"personal_story_backup_{datetime.datetime.now().isoformat()}")
                logger.warning(
                    f"Personal story of {ref_id} has {len(items_happened_later)} items happened after {time.game_time}, going to back it up to {backup_filename} and remove from the original story")

                self._save_personal_story(ref_id, story, backup_filename)
                story.items = items_happened_before

                self._save_personal_story(ref_id, story, "personal_story")

        return story
