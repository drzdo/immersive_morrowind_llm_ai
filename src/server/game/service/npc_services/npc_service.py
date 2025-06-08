import asyncio
from dataclasses import dataclass
from llm.session import LlmSession
from util.logger import Logger

from game.service.npc_services.npc_database import NpcDatabase
from eventbus.data.actor_ref import ActorRef
from eventbus.data.npc_data import NpcData
from eventbus.rpc import Rpc
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
from eventbus.event_data.event_data_rpc import EventDataRpc
from game.data.npc import Npc
from game.data.npc_behavior import NpcBehavior
from game.data.story import Story
from game.service.providers.env_provider import EnvProvider
from game.service.npc_services.npc_personality_generator import NpcPersonalityGenerator
from util.distance import Distance
from util.now_ms import now_ms

logger = Logger(__name__)


@dataclass
class _NpcInMemory:
    npc: Npc
    npc_data_expire_at_ms: int


class NpcService:
    def __init__(self, consumer: EventConsumer, rpc: Rpc, db: NpcDatabase, env_provider: EnvProvider,
                 llm_session: LlmSession) -> None:
        self._rpc = rpc
        self._db = db
        self._npc_personality_generator = NpcPersonalityGenerator(llm_session)

        self._env_provider = env_provider

        self._ref_id_to_npc: dict[str, _NpcInMemory] = {}
        self._npc_data_expiration_ms = 30_000
        self._npc_ref_id_being_queried: set[str] = set()

        consumer.register_handler(self._handle_event)

    def clear_cache(self):
        self._ref_id_to_npc.clear()

    async def get_npc(self, npc_ref_id: str) -> Npc:
        while npc_ref_id in self._npc_ref_id_being_queried:
            await asyncio.sleep(1.0 / 30.0)

        self._npc_ref_id_being_queried.add(npc_ref_id)
        try:
            # memory
            npc_in_memory = self._ref_id_to_npc.get(npc_ref_id, None)
            if npc_in_memory:
                if now_ms() > npc_in_memory.npc_data_expire_at_ms:
                    npc_in_memory.npc.npc_data = await self._rpc.get_npc_data(npc_ref_id)
                    self._db.save_npc_data(npc_in_memory.npc)

                return npc_in_memory.npc

            # db
            npc_from_db = self._get_from_database(npc_ref_id)
            if npc_from_db:
                self._ref_id_to_npc[npc_ref_id] = _NpcInMemory(
                    npc_from_db,
                    now_ms() + self._npc_data_expiration_ms
                )

                npc_from_db.npc_data = await self._rpc.get_npc_data(npc_ref_id)
                self._db.save_npc_data(npc_from_db)
                return npc_from_db

            # game
            npc_data_from_game = await self._rpc.get_npc_data(npc_ref_id)
            new_npc = await self._create_new_npc(npc_data_from_game)
            self._ref_id_to_npc[npc_ref_id] = _NpcInMemory(
                new_npc,
                now_ms() + self._npc_data_expiration_ms
            )
            return new_npc
        finally:
            self._npc_ref_id_being_queried.remove(npc_ref_id)

    async def get_npcs_who_can_hear_another_actor(self, another_actor: ActorRef) -> list[Npc]:
        data = EventDataRpc.GetActorsNearbyRequest(
            type='get_actors_nearby_request',
            actor_ref_id=another_actor.ref_id,
            radius_ingame=Distance.from_meters_to_ingame(50),
            test_line_of_sight=True
        )
        response = await self._rpc.get_actors_nearby(data)

        npcs: list[Npc] = []
        for actor in response.actors:
            if actor.actor_ref.type == 'creature':
                if actor.actor_ref.ref_id not in ['vivec_god00000000']:
                    continue

            if not actor.can_see and Distance.from_ingame_to_meters(actor.distance_ingame) > 3:
                continue

            npc = await self.get_npc(actor.actor_ref.ref_id)
            if npc.npc_data.is_dead:
                continue

            npc.npc_data.player_distance = actor.distance_ingame

            npcs.append(npc)

        return npcs

    async def _handle_event(self, event: Event):
        if event.data.type == 'npc_death':
            if event.data.actor.ref_id in self._ref_id_to_npc:
                npc = self._ref_id_to_npc[event.data.actor.ref_id]
                npc.npc.npc_data.is_dead = True

    def _get_from_database(self, npc_ref_id: str) -> Npc | None:
        now = self._env_provider.now()
        story = self._db.load_personal_story(npc_ref_id, now)
        behavior = self._db.load_npc_behavior(npc_ref_id, now)
        personality = self._db.load_npc_personality(npc_ref_id, now)

        npc_data: NpcData | None = None
        try:
            npc_data = self._db.load_npc_data(npc_ref_id, now)
        except Exception as error:
            logger.warning(f"Npc data failed to load from DB: {error}")
            return None

        if npc_data and story and behavior and personality:
            npc = Npc(
                actor_ref=ActorRef(ref_id=npc_ref_id, type='npc', name=npc_data.name, female=npc_data.female),
                npc_data=npc_data,
                personality=personality,
                personal_story=story,
                behavior=behavior
            )
            return npc
        elif npc_data or story or behavior or personality:
            logger.error(f"NPC {npc_ref_id} has partial data locally")
            logger.debug(f"""npc_data={npc_data is not None} story={story is not None} behavior={
                behavior is not None} personality={personality is not None}""")
            return None
        else:
            return None

    async def _create_new_npc(self, npc_data: NpcData) -> Npc:
        logger.info(f"Generating new NPC context for {npc_data.ref_id}")

        npc = Npc(
            actor_ref=ActorRef(ref_id=npc_data.ref_id, type='npc', name=npc_data.name, female=npc_data.female),
            npc_data=npc_data,
            personality=await self._npc_personality_generator.generate(npc_data, self._env_provider.now().game_time),
            personal_story=Story(items=[]),
            behavior=NpcBehavior(
                last_processed_story_item_id=None,
                relation_to_other_npc={}
            )
        )

        self._db.save_npc_data(npc)
        self._db.save_npc_personality(npc)
        self._db.save_personal_story(npc)
        self._db.save_npc_behavior(npc)

        return npc
