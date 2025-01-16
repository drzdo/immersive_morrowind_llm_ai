
from typing import NamedTuple, Optional

from eventbus.data.actor_ref import ActorRef
from eventbus.data.position import Position


class PlayerRefLookedAt(NamedTuple):
    ref_id: str
    object_type: int
    name: Optional[str]
    owner: Optional[ActorRef]
    position: Position

    last_update_ms: int
