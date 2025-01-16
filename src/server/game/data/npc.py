from pydantic import BaseModel

from eventbus.data.actor_ref import ActorRef
from eventbus.data.npc_data import NpcData
from game.data.npc_behavior import NpcBehavior
from game.data.npc_personality import NpcPersonality
from game.data.story import Story


class Npc(BaseModel):
    actor_ref: ActorRef
    npc_data: NpcData

    personality: NpcPersonality
    personal_story: Story

    behavior: NpcBehavior

    def __str__(self) -> str:
        return self.actor_ref.__str__()
