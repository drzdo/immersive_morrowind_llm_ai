import asyncio
import random
import traceback
from app.app_config import AppConfig
from eventbus.event import Event
from eventbus.event_data.event_data_from_server import EventDataFromServer
from eventbus.event_producer import EventProducer
from game.service.npc_services.npc_intention_analyzer import NpcIntentionAnalyzer
from game.service.npc_services.npc_speaker_service import NpcSpeakerService
from game.service.player_services.player_personal_story_service import PlayerPersonalStoryService
from game.service.providers.cell_name_provider import CellNameProvider
from game.service.util.text_sanitizer import TextSanitizer
from util.colored_lines import green
from util.logger import Logger
from typing import Optional
from pynput import keyboard

from eventbus.event_consumer import EventConsumer
from game.data.npc import Npc
from game.data.story_item import StoryItemData, StoryItemDataAlias
from game.i18n.i18n import I18n
from game.service.providers.dialog_provider import DialogProvider
from game.service.providers.env_provider import EnvProvider
from game.service.event_producers.event_producer_from_story import EventProducerFromStory
from game.service.player_services.player_intention_analyzer import PlayerIntentionAnalyzer
from game.service.npc_services.npc_behavior_service import NpcBehaviorService
from game.service.npc_services.npc_personal_story_service import NpcPersonalStoryService
from game.service.npc_services.npc_service import NpcService
from game.service.player_services.player_provider import PlayerProvider
from eventbus.data.actor_ref import ActorRef
from game.service.player_services.local_player_speaking_listener import LocalPlayerSpeakingListener
from util.now_ms import now_ms

logger = Logger(__name__)

class GameMaster:
    def __init__(
        self,
        config: AppConfig,
        event_producer: EventProducer,
        event_consumer: EventConsumer,
        player_provider: PlayerProvider,
        player_story_service: PlayerPersonalStoryService,
        dialog_provider: DialogProvider,
        env_provider: EnvProvider,
        npc_service: NpcService,
        npc_behavior_service: NpcBehaviorService,
        npc_speaker_service: NpcSpeakerService,
        npc_personal_story_service: NpcPersonalStoryService,
        event_producer_from_story: EventProducerFromStory,
        player_intention_analyzer: PlayerIntentionAnalyzer,
        npc_intention_analyzer: NpcIntentionAnalyzer,
        text_sanitizer: TextSanitizer,
        i18n: I18n,
        cell_name_provider: CellNameProvider
    ) -> None:
        self._config = config
        self._event_producer = event_producer
        self._player_provider = player_provider
        self._player_story_service = player_story_service
        self._player_speak_listener = LocalPlayerSpeakingListener(event_consumer, self._on_local_player_speak)

        self._dialog_provider = dialog_provider
        self._env_provider = env_provider
        self._npc_service = npc_service
        self._npc_behavior_service = npc_behavior_service
        self._npc_speaker_service = npc_speaker_service
        self._npc_personal_story_service = npc_personal_story_service
        self._event_producer_from_story = event_producer_from_story

        self._player_intention_analyzer = player_intention_analyzer
        self._npc_intention_analyzer = npc_intention_analyzer
        self._npc_continuous_chat_start_at_generation_index: int = -1

        self._text_sanitizer = text_sanitizer
        self._i18n = i18n
        self._cell_name_provider = cell_name_provider

        self._publish_lock = asyncio.Lock()
        self._player_was_going_to_act_last_time = False
        self._last_shut_up_command_ms = 0

        self._listener_k = keyboard.Listener(
            on_press=self._handle_press,  # type: ignore
            on_release=self._handle_release)  # type: ignore
        self._pause_story_loop = False
        self._listener_k.start()

        event_consumer.register_handler(self._handler)

        asyncio.get_event_loop().create_task(self._progress_story_loop())

    def start(self):
        self._player_story_service.publish_player_story()

    def _handle_press(self, key: keyboard.Key):
        if hasattr(key, 'vk') and key.__getattribute__('vk') == 96:  # NumPad0
            self._pause_story_loop = not self._pause_story_loop
            if self._pause_story_loop:
                logger.info("Story progression PAUSED")
            else:
                self._npc_service.clear_cache()
                logger.info("Story progression RESUMED")

    def _handle_release(self, key):  # type: ignore
        pass

    async def _progress_story_loop(self):
        while True:
            await asyncio.sleep(1.0)

            if self._npc_speaker_service.is_scene_locked():
                continue

            if (now_ms() - self._last_shut_up_command_ms) < 5:
                continue

            if self._pause_story_loop:
                continue

            await self._determine_npc_to_act_and_act()

    async def _handler(self, event: Event):
        if event.data.type == 'npc_death':
            await self._register_and_process_new_incoming_story_item_data_list(
                place=event.data.type,
                item_data_list=[
                    StoryItemData.NpcDeath(
                        type='npc_death',
                        victim=event.data.actor,
                        killer=event.data.killer
                    )
                ]
            )
        elif event.data.type == 'ashfall_eat_stew':
            if self._dialog_provider.npc_ref:
                await self._register_and_process_new_incoming_story_item_data_list(
                    place=event.data.type,
                    item_data_list=[
                        StoryItemData.AshfallEatStew(
                            type='ashfall_eat_stew',
                            cost=event.data.cost,
                            stew_name=event.data.stew_name,
                            initiator=self._player_provider.local_player.actor_ref,
                            seller=self._dialog_provider.npc_ref
                        )
                    ]
                )
        elif event.data.type == 'barter_offer':
            if self._dialog_provider.npc_ref:
                await self._register_and_process_new_incoming_story_item_data_list(
                    place=event.data.type,
                    item_data_list=[
                        StoryItemData.BarterOffer(
                            type='barter_offer',
                            buying=event.data.buying,
                            buyer=self._player_provider.local_player.actor_ref,
                            merchant=event.data.merchant,
                            offer=event.data.offer,
                            selling=event.data.selling,
                            success=event.data.success,
                            value=event.data.value
                        )
                    ]
                )
        elif event.data.type == 'cell_changed':
            data = StoryItemData.PlayerCellChanged(
                type='player_cell_changed',
                initiator=self._player_provider.local_player.actor_ref,
                cell=event.data.cell
            )
            data.cell.display_name = self._cell_name_provider.get_cell_name(data.cell.display_name)

            await self._register_and_process_new_incoming_story_item_data_list(
                place=event.data.type,
                item_data_list=[data]
            )

            hearable_npcs = await self._get_npcs_who_can_hear_player(None)
            hearable_actors = list(map(lambda n: n.actor_ref, hearable_npcs))
            await self._npc_speaker_service.npcs_shut_up(lambda a: a not in hearable_actors)

    async def _on_local_player_speak(self, text: str):
        item_data_list_from_player = await self._determine_story_item_data_from_player_saying(text)

        await self._register_and_process_new_incoming_story_item_data_list(
            place="player_says",
            item_data_list=item_data_list_from_player
        )

    def _get_player_target(self):
        if self._dialog_provider.is_in_dialog and self._dialog_provider.npc_ref:
            return self._dialog_provider.npc_ref
        else:
            return self._player_speak_listener.player_stopped_speaking_looking_at or self._player_speak_listener.player_started_speaking_looking_at

    async def _register_and_process_new_incoming_story_item_data_list(
        self,
        *,
        place: str,
        item_data_list: list[StoryItemDataAlias]
    ):
        await self._publish_lock.acquire()
        try:
            target = self._get_player_target()
            hearing_npcs = await self._get_npcs_who_can_hear_player(target)
            if len(hearing_npcs) == 0:
                logger.debug("Nobody hears the player, skip updating stories")
                return

            await self._add_to_story_and_publish_events(
                place,
                hearing_npcs,
                item_data_list
            )
        finally:
            self._publish_lock.release()

    async def _determine_npc_to_act_and_act(self):
        try:
            await self._publish_lock.acquire()
            scene_lock_generation_id = self._npc_speaker_service.lock_scene()

            target = self._get_player_target()
            hearing_npcs = await self._get_npcs_who_can_hear_player(target)
            actor_pick_response = await self._npc_behavior_service.decide_who_should_act(self._player_provider.local_player, target, hearing_npcs)

            if not self._npc_speaker_service.is_scene_locked_at(scene_lock_generation_id):
                logger.debug("Cancel determining NPC to act, scene lock was retired (1)")
                return

            actor_to_act = actor_pick_response.actor_to_act

            if len(actor_pick_response.reason) > 0:
                self._player_story_service.add_items_to_personal_story([
                    StoryItemData.ActorPickReason(
                        type='actor_pick_reason',
                        actor=actor_to_act,
                        reason=actor_pick_response.reason if actor_pick_response.pass_reason_to_npc else ""
                    )
                ])

            all_actors: list[ActorRef] = [
                self._player_provider.local_player.actor_ref
            ]
            for npc in hearing_npcs:
                all_actors.append(npc.actor_ref)
            all_actors.remove(actor_to_act)

            # self._npc_speaker_service.turn_to_actor(all_actors, actor_to_act)
            for actor in all_actors:
                asyncio.get_event_loop().call_later(
                    random.uniform(0.0, 2.0),
                    self._npc_speaker_service.turn_to_actor,
                    [actor], actor_to_act
                )

            if actor_to_act.type == 'player':
                if not self._player_was_going_to_act_last_time:
                    logger.info(f"Player is going to act this time")
                    self._player_was_going_to_act_last_time = True

                if self._npc_speaker_service.is_scene_locked_at(scene_lock_generation_id):
                    self._npc_speaker_service.unlock_scene()
                return

            npc_to_act = await self._npc_service.get_npc(actor_to_act.ref_id)
            self._player_was_going_to_act_last_time = False

            if not self._npc_speaker_service.is_scene_locked_at(scene_lock_generation_id):
                logger.debug("Cancel determining NPC to act, scene lock was retired (2)")
                return

            scene_hold = self._npc_speaker_service.set_scene_holder(scene_lock_generation_id, npc_to_act.actor_ref)
            if not scene_hold:
                logger.info(f"NPC {npc_to_act.actor_ref} was about to act but scene lock was taken over")

            logger.info(f"NPC {npc_to_act.actor_ref} is going to act")
            other_hearing_npcs = hearing_npcs.copy()
            other_hearing_npcs.remove(npc_to_act)

            request = NpcBehaviorService.Request(
                npc=npc_to_act,
                other_hearing_npcs=other_hearing_npcs,
                is_in_dialog=self._dialog_provider.is_in_dialog,
                known_topics=self._dialog_provider.topics,
                reasoning=actor_pick_response.reason,
                player_ref_looked_at=self._player_speak_listener.player_last_ref_looked_at
            )
            response = await self._npc_behavior_service.decide_how_npc_should_act(request)

            if not self._npc_speaker_service.is_scene_locked_by(npc_to_act.actor_ref):
                logger.info(
                    f"Cancelling NPC {npc_to_act.actor_ref} response because no more holding the scene lock")
                return

            await self._handle_npc_behavior_process_response(request, response)
        except Exception as error:
            logger.error(f"Error happened while scene was locked: {error}")
            logger.debug(traceback.format_exc())

            if self._npc_speaker_service.is_scene_locked():
                self._npc_speaker_service.unlock_scene()
        finally:
            self._publish_lock.release()

    async def _get_npcs_who_can_hear_player(self, target_ref: Optional[ActorRef]):
        hearing_npcs = await self._npc_service.get_npcs_who_can_hear_another_actor(self._player_provider.local_player.actor_ref)

        if target_ref and target_ref.type == 'npc':
            target_npc = await self._npc_service.get_npc(target_ref.ref_id)
            if target_npc not in hearing_npcs:
                hearing_npcs.append(target_npc)

        return hearing_npcs

    async def _determine_story_item_data_from_player_saying(self, text_raw: str) -> list[StoryItemDataAlias]:
        target_ref = self._get_player_target()
        known_topics = list(map(lambda topic: topic.topic_text, self._dialog_provider.topics))

        text = self._text_sanitizer.sanitize(text_raw)
        player_intention = await self._player_intention_analyzer.analyze_player_intention(text, known_topics, target_ref)

        item_data_list_from_player: list[StoryItemDataAlias] = []

        should_add_original_say_text = True
        if player_intention.trigger_dialog_topic:
            if target_ref:
                item_data_list_from_player.append(
                    StoryItemData.PlayerTriggerDialogTopic(
                        type='player_trigger_dialog_topic',
                        speaker=self._player_provider.local_player.actor_ref,
                        target=target_ref,
                        original_text=text,
                        trigger_topic=player_intention.trigger_dialog_topic
                    )
                )
                should_add_original_say_text = False
            else:
                logger.warning(f"Player triggerred topic {player_intention.trigger_dialog_topic} without a target NPC")
        elif player_intention.list_available_dialog_topics:
            if target_ref:
                item_data_list_from_player.append(
                    StoryItemData.PlayerTriggerListDialogTopics(
                        type='player_trigger_list_dialog_topics',
                        speaker=self._player_provider.local_player.actor_ref,
                        target=target_ref,
                        original_text=text
                    )
                )
                should_add_original_say_text = False
            else:
                logger.warning(f"Player triggerred listing of topics without a target NPC")
        else:
            if player_intention.npc_shut_up:
                self._last_shut_up_command_ms = now_ms()

                item_data_list_from_player.append(
                    StoryItemData.PlayerTellsToShutUp(
                        type='player_tells_to_shut_up',
                        speaker=self._player_provider.local_player.actor_ref
                    )
                )

                await self._npc_speaker_service.npcs_shut_up(lambda a: True)

            if player_intention.npc_stop_follow:
                if target_ref:
                    item_data_list_from_player.append(
                        StoryItemData.NpcStopFollow(
                            type='npc_stop_follow',
                            initiator=self._player_provider.local_player.actor_ref,
                            target=target_ref
                        )
                    )

            if player_intention.npc_stop_combat:
                item_data_list_from_player.append(
                    StoryItemData.PlayerTellsToStopCombat(
                        type='player_tells_to_stop_combat',
                        speaker=self._player_provider.local_player.actor_ref
                    )
                )

                self._last_shut_up_command_ms = now_ms()
                await self._npc_speaker_service.npcs_shut_up(lambda a: True)

                hearing_npcs = await self._get_npcs_who_can_hear_player(target_ref)
                for npc in hearing_npcs:
                    self._event_producer.produce_event(Event(
                        data=EventDataFromServer.NpcStopCombat(
                            type='npc_stop_combat',
                            npc_ref_id=npc.actor_ref.ref_id
                        )
                    ))

            if player_intention.sheogorath_level:
                logger.info(f"{green('Sheogorath')} level: {player_intention.sheogorath_level}")
                item_data_list_from_player.append(
                    StoryItemData.PlayerTriggerSheogorathLevel(
                        type='player_trigger_sheogorath_level',
                        speaker=self._player_provider.local_player.actor_ref,
                        sheogorath_level=player_intention.sheogorath_level
                    )
                )

            if self._player_speak_listener.player_last_ref_looked_at:
                ref = self._player_speak_listener.player_last_ref_looked_at
                if (now_ms() - ref.last_update_ms) < 10000 and ref.name:
                    item_data_list_from_player.append(
                        StoryItemData.PlayerPointsAtRef(
                            type='player_points_at_ref',
                            speaker=self._player_provider.local_player.actor_ref,
                            target_ref_id=ref.ref_id,
                            target_name=ref.name,
                            target_owner=ref.owner,
                            target_position=ref.position
                        )
                    )

        if should_add_original_say_text:
            item_data_list_from_player.insert(
                0,
                StoryItemData.SayProcessed(
                    type='say_processed',
                    speaker=self._player_provider.local_player.actor_ref,
                    target=target_ref,
                    text=text,
                    audio_duration_sec=None
                )
            )

        return item_data_list_from_player

    async def _handle_npc_behavior_process_response(
        self,
        request: NpcBehaviorService.Request,
        response: NpcBehaviorService.Response
    ):
        if not response.is_behavior_updated:
            logger.debug(f"Noop in NPC behavior response as behavior is not updated: {response}")
            return
        if len(response.item_data_list) == 0:
            logger.debug(f"Noop in NPC behavior response as item data list is empty: {response}")
            return

        logger.debug(f"NPC behavior response is: {response}")

        all_hearing_npcs = request.other_hearing_npcs.copy()
        all_hearing_npcs.append(request.npc)

        new_item_data_list: list[StoryItemDataAlias] = []
        for data in response.item_data_list:
            processed_data_list = await self._npc_intention_analyzer.process_story_item_data(all_hearing_npcs, data)
            new_item_data_list.extend(processed_data_list)

        if not self._npc_speaker_service.is_scene_locked_by(request.npc.actor_ref):
            logger.debug("Cancel handling NPC behavior because scene is unlocked (3)")
            return

        if not self._config.text_to_speech.sync_print_and_speak:
            await self._add_to_story_and_publish_events(
                'npc_response',
                all_hearing_npcs,
                new_item_data_list
            )

        for d in new_item_data_list:
            if d.type == 'say_processed' and d.speaker.type == 'npc':
                if d.speaker == request.npc.actor_ref:
                    audio_duration_sec = await self._npc_speaker_service.say(request.npc, d.text, d.target)
                    d.audio_duration_sec = audio_duration_sec
                else:
                    logger.error(f"Other NPC {d.speaker} wants to speak but request is for {request.npc.actor_ref}")
            elif d.type == 'npc_trigger_dialog_topic':
                if d.speaker == request.npc.actor_ref:
                    text = self._text_sanitizer.sanitize(d.topic_response, npc_data=request.npc.npc_data)
                    audio_duration_sec = await self._npc_speaker_service.say(request.npc, text, d.target)
                else:
                    logger.error(f"Other NPC {d.speaker} wants to speak but request is for {request.npc.actor_ref}")

        if self._config.text_to_speech.sync_print_and_speak:
            await self._add_to_story_and_publish_events(
                'npc_response',
                all_hearing_npcs,
                new_item_data_list
            )

    async def _add_to_story_and_publish_events(
        self,
        place: str,
        npcs_to_add_to: list[Npc],
        item_data_list: list[StoryItemDataAlias]
    ):
        self._add_to_story(place, npcs_to_add_to, item_data_list)
        await self._publish_events(item_data_list)

    def _add_to_story(
        self,
        place: str,
        npcs_to_add_to: list[Npc],
        item_data_list: list[StoryItemDataAlias]
    ):
        logger.debug(f"""Adding story items place={place}
    npcs={",".join(map(lambda npc: npc.npc_data.name, npcs_to_add_to))}
    item_data_list={item_data_list}""")

        self._player_story_service.add_items_to_personal_story(item_data_list)
        self._npc_personal_story_service.add_items_to_personal_stories(npcs_to_add_to, item_data_list)

    async def _publish_events(self, item_data_list: list[StoryItemDataAlias]):
        await self._event_producer_from_story.publish_events_from_items(
            item_data_list,
            self._dialog_provider.npc_ref if self._dialog_provider.is_in_dialog else None)
