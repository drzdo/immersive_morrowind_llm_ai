from pydantic import BaseModel
from database.database import Database
from eventbus.data.actor_ref import ActorRef
from eventbus.data.npc_data import NpcData
from game.data.npc import Npc, NpcMemory
from game.data.story import Story
from tts.voice import Voice
from util.logger import Logger

logger = Logger(__name__)


class NpcDatabase:
    class Config(BaseModel):
        max_stored_story_items: int
        max_used_in_llm_story_items: int

    def __init__(self, config: Config, db: Database):
        self._config = config
        self._db = db

    def save_npc(self, npc: Npc):
        ref_id = npc.actor_ref.ref_id

        self._db.save_model(path=['npc', ref_id, 'actor_ref'], value=npc.actor_ref)
        self._db.save_model(path=['npc', ref_id, 'npc_data'], value=npc.npc_data)
        self._db.save_model(path=['npc', ref_id, 'personal_story'], value=npc.personal_story)
        self._db.save_model(path=['npc', ref_id, 'voice'], value=npc.voice)
        self._db.save_model(path=['npc', ref_id, 'memory'], value=npc.memory)

    def load_npc(self, ref_id: str) -> Npc | None:
        if not self._db.exists(path=['npc', ref_id]):
            return None

        return Npc(
            actor_ref=self._db.load_model_force(type=ActorRef, path=['npc', ref_id, 'actor_ref']),
            npc_data=self._db.load_model_force(type=NpcData, path=['npc', ref_id, 'npc_data']),
            personal_story=self._db.load_model_force(type=Story, path=['npc', ref_id, 'personal_story']),
            voice=self._db.load_model_force(type=Voice, path=['npc', ref_id, 'voice']),
            memory=self._db.load_model_force(type=NpcMemory, path=['npc', ref_id, 'memory'])
        )
