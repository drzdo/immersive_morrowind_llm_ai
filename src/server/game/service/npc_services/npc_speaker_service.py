import asyncio
import traceback
from typing import Callable
import mutagen.mp3
from pydantic import BaseModel, Field
from eventbus.data.actor_ref import ActorRef
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
from eventbus.event_data.event_data_from_server import EventDataFromServer
from eventbus.event_producer import EventProducer
from game.data.npc import Npc
from game.service.npc_services.npc_service import NpcService
from game.service.player_services.player_provider import PlayerProvider
from tts.request import TtsRequest
from tts.response import TtsResponse
from tts.system import TtsSystem
from util.distance import Distance
from util.logger import Logger

logger = Logger(__name__)


class _SceneLock:
    def __init__(self) -> None:
        self._is_locked = False
        self._generation = 1
        self._holder: ActorRef | None = None

    def locked(self):
        return self._is_locked

    @property
    def generation(self):
        return self._generation

    def lock(self):
        if self._is_locked:
            logger.error("Trying to lock scene while it is locked")
            logger.debug(traceback.format_stack())
            raise Exception("Trying to lock scene while it is locked")

        else:
            self._is_locked = True
            self._generation = self._generation + 1

        return self._generation

    @property
    def holder(self):
        return self._holder

    def set_holder(self, generation_id: int, holder: ActorRef) -> bool:
        if not self._is_locked:
            logger.error(f"Trying to set holder before locking the scene: holder={holder}")
            logger.debug(traceback.format_stack())
            raise Exception("Trying to set holder before locking the scene")

        if generation_id != self._generation:
            return False

        self._holder = holder
        return True

    def unlock(self):
        self._is_locked = False
        self._holder = None
        self._generation = self._generation + 1

    def unlock_later_if_same_generation(self, delay_s: float):
        current_generation = self._generation
        asyncio.get_event_loop().call_later(
            delay_s,
            lambda: self._unlock_if_same_generation(current_generation)
        )

    def _unlock_if_same_generation(self, expected_generation: int):
        if self._generation == expected_generation:
            logger.debug("Lock scene was acquired and got timed out. Going to unlock...")
            self.unlock()


class _ActorLock:
    def __init__(self, actor: ActorRef):
        self._actor = actor
        self._lock = asyncio.Lock()
        self._generation = 1

    async def acquire(self, timeout_s: float):
        logger.debug(f"Acquiring lock {self._actor}...")

        await self._lock.acquire()
        self._generation = self._generation + 1

        logger.debug(f"Lock {self._actor} is acquired")

        self._release_later_if_same_generation(timeout_s)

    def release(self):
        self._lock.release()
        self._generation = self._generation + 1

        logger.debug(f"Lock {self._actor} is released")

    def locked(self):
        return self._lock.locked()

    def _release_later_if_same_generation(self, delay_s: float):
        current_generation = self._generation
        asyncio.get_event_loop().call_later(
            delay_s,
            lambda: self._release_if_same_generation(current_generation)
        )

    def _release_if_same_generation(self, expected_generation: int):
        if self._generation == expected_generation:
            logger.debug(f"Lock {self._actor} was acquired and got timed out. Going to release...")
            self.release()


class NpcSpeakerService:
    class Config(BaseModel):
        release_before_end_sec: float = Field(default=4)

    def __init__(self, config: Config, consumer: EventConsumer, producer: EventProducer, player_provider: PlayerProvider, tts: TtsSystem,
                 npc_service: NpcService) -> None:
        self._config = config
        self._consumer = consumer
        self._producer = producer
        self._player_provider = player_provider
        self._tts = tts
        self._npc_service = npc_service

        self._scene_lock_timeout_s: int = 90

        self._scene_lock = _SceneLock()
        self._actor_lock: dict[ActorRef, _ActorLock] = {}

        consumer.register_handler(self._handle_event)

    async def _handle_event(self, event: Event):
        if event.data.type == 'npc_death':
            actor_lock = self._get_actor_lock(event.data.actor)
            if actor_lock.locked():
                actor_lock.release()
                await self._remove_actor_sound(event.data.actor)

            if event.data.actor == self._scene_lock.holder:
                logger.debug("Npc is dead now and holding the lock, releasing")
                self._scene_lock.unlock()
        elif event.data.type == 'stt_recognition_update':
            if len(event.data.text) > 0 and self._scene_lock.holder != self._player_provider.local_player.actor_ref:
                logger.debug("Player started speaking, acquire the lock")

                # for actor in self._actor_lock:
                #     actor_lock = self._actor_lock[actor]
                #     if actor_lock.locked():
                #         actor_lock.release()
                #         await self._remove_actor_sound(actor)

                if self._scene_lock.locked():
                    self._scene_lock.unlock()

                generation_id = self._scene_lock.lock()
                self._scene_lock.set_holder(generation_id, self._player_provider.local_player.actor_ref)
        elif event.data.type == 'stt_recognition_complete':
            if self._scene_lock.holder == self._player_provider.local_player.actor_ref:
                logger.debug("Player stopped speaking, release the player's lock")
                self._scene_lock.unlock()
            else:
                logger.warning("Player stopped speaking, but not holder of the lock, skip unlock")

    async def npcs_shut_up(self, should_shut_npc_up: Callable[[ActorRef], bool]):
        logger.info("Shut NPCs up")

        for actor in self._actor_lock:
            actor_lock = self._actor_lock[actor]
            if actor_lock.locked() and should_shut_npc_up(actor):
                actor_lock.release()
                await self._remove_actor_sound(actor)

        if self._scene_lock.locked() and (self._scene_lock.holder is None or self._scene_lock.holder.type == 'npc'):
            self._scene_lock.unlock()

    def lock_scene(self):
        return self._scene_lock.lock()

    def unlock_scene(self):
        self._scene_lock.unlock()

    def is_scene_locked(self):
        return self._scene_lock.locked()

    def is_scene_locked_at(self, generation: int):
        return self._scene_lock.locked() and self._scene_lock.generation == generation

    def is_scene_locked_by(self, holder: ActorRef):
        return self._scene_lock.locked() and self._scene_lock.holder == holder

    def set_scene_holder(self, generation_id: int, holder: ActorRef):
        self._scene_lock.set_holder(generation_id, holder)

    async def say(self, npc: Npc, text: str, target: ActorRef | None):
        if not self._scene_lock.locked():
            logger.debug(f"Say is called for {npc.actor_ref} but scene is not locked, skipping say")
            return

        if self._scene_lock.holder != npc.actor_ref:
            logger.debug(
                f"Say is called for NPC who does not hold the lock: npc={npc.actor_ref} holder={self._scene_lock.holder}")
            return

        tts_response = await self._produce_voiceover(npc, text)

        if tts_response is None:
            logger.debug(f"Empty TTS response, skip: npc={npc.actor_ref}")
            self.unlock_scene()
            return

        if self._scene_lock.holder != npc.actor_ref:
            logger.debug(
                f"After TTS NPC does not hold the scene lock anymore: npc={npc.actor_ref} holder={self._scene_lock.holder}")
            return

        if npc.npc_data.is_dead:
            logger.debug(f"Npc got dead, skip: npc={npc.actor_ref}")
            self.unlock_scene()
            return

        audio_duration_sec = mutagen.mp3.MP3(tts_response.file_path).info.length

        actor_lock_timeout = audio_duration_sec
        await self._get_actor_lock(npc.actor_ref).acquire(actor_lock_timeout)

        if self._scene_lock.holder != npc.actor_ref:
            self._get_actor_lock(npc.actor_ref).release()
            logger.debug(
                f"After getting actor lock NPC does not hold the scene lock anymore: npc={npc.actor_ref} holder={self._scene_lock.holder}")
            return

        if npc.npc_data.is_dead:
            logger.debug(f"Npc got dead while getting the actor lock, skip: npc={npc.actor_ref}")
            self._get_actor_lock(npc.actor_ref).release()
            self.unlock_scene()
            return

        logger.debug(f"Actor will be unlocked in {actor_lock_timeout} sec")

        scene_lock_timeout = max(1, audio_duration_sec - self._config.release_before_end_sec)
        self._scene_lock.unlock_later_if_same_generation(scene_lock_timeout)
        logger.debug(f"Scene will be unlocked in {scene_lock_timeout} sec")

        self._send_say_mp3_event(npc, text, target, tts_response, audio_duration_sec)

    def turn_to_actor(self, actors: list[ActorRef], target: ActorRef):
        self._producer.produce_event(Event(
            data=EventDataFromServer.TurnActorsTo(
                type='turn_actors_to',
                target_ref_id=target.ref_id,
                actor_ref_ids=list(map(lambda a: a.ref_id, actors))
            )
        ))

    def _get_actor_lock(self, actor: ActorRef):
        if actor not in self._actor_lock:
            self._actor_lock[actor] = _ActorLock(actor)
        return self._actor_lock[actor]

    def _translit(self, s: str):
        cyr = "абвгдеёжзиклмнопрстуфхцчшщьыъэюя"
        eng = [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "yo",
            "zh",
            "z",
            "i",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "h",
            "ts",
            "tsh",
            "sh",
            "sch",
            "'",
            "yi",
            "'",
            "e",
            "yu",
            "ya",
        ]
        s_out = ""
        for c in s:
            с_lc = c.lower()
            c_out = c
            if с_lc in cyr:
                i = cyr.index(с_lc)
                c_out = eng[i]
            s_out = s_out + c_out
        return s_out

    def _translit_ashkhan(self, text: str):
        replaces = [
            "ться", "ца",
            "л", "ль",
            "ы", "и",
            "е", "и",
            "ш", "щь",
            "р", "рр",
            "х", "хх"
        ]
        for i in range(0, len(replaces), 2):
            src = replaces[i]
            dst = replaces[i + 1]
            text = text.replace(src, dst)
        return text

    async def _produce_voiceover(self, npc: Npc, text: str):
        text_processed = self._delete_non_verbal_comments(text)

        match npc.personality.voice.accent:
            case 'none':
                pass
            case 'translit':
                text_processed = self._translit(text_processed)
            case 'ashkhan':
                text_processed = self._translit_ashkhan(text_processed)

        tts_request = TtsRequest(text=text_processed, voice=npc.personality.voice)
        return await self._tts.convert(tts_request)

    def _send_say_mp3_event(self, npc: Npc, text: str, target: ActorRef | None,
                            tts_response: TtsResponse, duration_sec: float):
        vo_starts = tts_response.file_path.find("Vo\\")
        if vo_starts < 0:
            vo_starts = tts_response.file_path.find("Vo/")

        if vo_starts < 0:
            logger.error(f"Failed to convert audio path, cannot find Vo in it: {tts_response.file_path}, skip TTS")
            return

        adjusted_file_path = tts_response.file_path[vo_starts:]

        self._producer.produce_event(Event(
            data=EventDataFromServer.NpcSayMp3(
                type='npc_say_mp3',
                npc_ref_id=npc.actor_ref.ref_id,
                file_path=adjusted_file_path,
                pitch=1.0 if tts_response.is_pitch_already_applied else npc.personality.voice.pitch,
                target_ref_id=target.ref_id if target else None,
                duration_sec=duration_sec
            )
        ))

    async def _remove_actor_sound(self, actor: ActorRef):
        if actor.type == 'npc':
            npc = await self._npc_service.get_npc(actor.ref_id)
            distance_m = Distance.from_ingame_to_meters(
                npc.npc_data.position.distance(self._player_provider.local_player.player_data.position)
            )
            if distance_m < 20:
                logger.debug(f"Silencing {actor}")
                self._producer.produce_event(Event(
                    data=EventDataFromServer.NpcRemoveSound(
                        type='npc_remove_sound',
                        npc_ref_id=actor.ref_id
                    )
                ))

    def _delete_non_verbal_comments(self, text: str):
        while True:
            i0 = text.find('(')
            if i0 < 0:
                break

            i1 = text.find(')', i0 + 1)
            if i1 >= 0:
                text = text[:i0] + text[i1 + 1:]
            else:
                break
        while True:
            i0 = text.find('[')
            if i0 < 0:
                break

            i1 = text.find(']', i0 + 1)
            if i1 >= 0:
                text = text[:i0] + text[i1 + 1:]
            else:
                break
        # while True:
        #     i0 = text.find('*')
        #     if i0 >= 0:
        #         i1 = text.find('*', i0 + 1)
        #         if i1 >= 0:
        #             text = text[:i0] + text[i1 + 1:]
        #         else:
        #             break
        #     else:
        #         break

        text = text.replace("  ", " ")
        text = text.strip()
        return text
