from pydantic import BaseModel, Field

from game.data.story_item import StoryItem


class Story(BaseModel):
    next_item_id: int = Field(default=1)
    items: list[StoryItem] = Field(default=[])

    def return_next_item_id_and_inc(self):
        v = self.next_item_id
        self.next_item_id = self.next_item_id + 1
        return v
