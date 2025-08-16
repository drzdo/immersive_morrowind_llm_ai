from pydantic import BaseModel, Field

from eventbus.data.actor_ref import ActorRef
from eventbus.data.npc_data import NpcData
from game.data.story import Story
from tts.voice import Voice


class NpcMemoryEntry(BaseModel):
    fact: str
    interpretation: str


class NpcMemory(BaseModel):
    entries: list[NpcMemoryEntry] = Field(default_factory=lambda: [])
    update_rules: list[str] = Field(default_factory=lambda: [])


class Npc(BaseModel):
    actor_ref: ActorRef
    npc_data: NpcData

    personal_story: Story
    voice: Voice
    memory: NpcMemory

    def __str__(self) -> str:
        return self.actor_ref.__str__()
