from typing import Optional
from pydantic import BaseModel

class NpcBehavior(BaseModel):
    last_processed_story_item_id: Optional[int]
    relation_to_other_npc: dict[str, int]
