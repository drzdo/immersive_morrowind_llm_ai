from pydantic import BaseModel

from eventbus.data.player_data import PlayerData
from eventbus.data.actor_ref import ActorRef
from game.data.story import Story


class Player(BaseModel):
    actor_ref: ActorRef
    player_data: PlayerData
    personal_story: Story
