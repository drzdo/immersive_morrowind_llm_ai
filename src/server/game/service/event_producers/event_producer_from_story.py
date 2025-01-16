from typing import NamedTuple
from util.distance import Distance
from util.logger import Logger

from eventbus.data.actor_ref import ActorRef
from eventbus.event_data.event_data_from_server import EventDataFromServer, EventDataFromServerUnion
from eventbus.event_producer import EventProducer
from eventbus.event import Event
from game.data.story_item import StoryItemData, StoryItemDataAlias
from game.i18n.i18n import I18n
from game.service.npc_services.npc_service import NpcService
from game.service.player_services.player_provider import PlayerProvider

logger = Logger(__name__)


class _NpcSayAccumulatedContext(NamedTuple):
    say_data: StoryItemData.SayProcessed
    reaction_list: list[str]


class EventProducerFromStory:
    def __init__(self, producer: EventProducer, player_provider: PlayerProvider, npc_service: NpcService, i18n: I18n) -> None:
        self._producer = producer
        self._player_provider = player_provider
        self._npc_service = npc_service
        self._i18n = i18n

    async def publish_events_from_items(
        self,
        item_data_list: list[StoryItemDataAlias]
    ):
        logger.debug(f"Going to publish events from item data list: {item_data_list}")

        say_ctx: _NpcSayAccumulatedContext | None = None
        flushed_say_ctx: list[_NpcSayAccumulatedContext] = []

        event_data_to_send: list[EventDataFromServerUnion] = []

        for data in item_data_list:
            try:
                if data.type == 'say_processed':
                    if say_ctx:
                        flushed_say_ctx.append(say_ctx)

                    say_ctx = _NpcSayAccumulatedContext(data, [])
                elif data.type == 'npc_trigger_dialog_topic':
                    event_data_to_send.append(
                        EventDataFromServer.TriggerTopicInDialog(
                            type='trigger_topic_in_dialog',
                            topic=data.topic_name
                        )
                    )
                elif data.type == 'npc_pick_up_item':
                    event_data_to_send.append(
                        EventDataFromServer.NpcActivate(
                            type='npc_activate',
                            npc_ref_id=data.initiator.ref_id,
                            target_ref_id=data.item_ref_id,
                            dropped_item_id=data.dropped_item_id
                        )
                    )
                elif data.type == 'npc_attack':
                    event_data_to_send.append(
                        EventDataFromServer.NpcStartCombat(
                            type='npc_start_combat',
                            npc_ref_id=data.initiator.ref_id,
                            target_ref_id=data.victim.ref_id,
                        )
                    )
                elif data.type == 'npc_drop_item':
                    event_data_to_send.append(
                        EventDataFromServer.NpcSpawnItem(
                            type='npc_spawn_item',
                            npc_ref_id=data.initiator.ref_id,
                            count=data.count,
                            item=data.item_id,
                            water_amount=data.water_amount
                        )
                    )
                elif data.type == 'npc_come':
                    event_data_to_send.append(
                        EventDataFromServer.NpcTravel(
                            type='npc_travel',
                            npc_ref_id=data.initiator.ref_id,
                            target_ref_id=data.target.ref_id
                        )
                    )
                elif data.type == 'npc_stop_follow':
                    event_data_to_send.append(EventDataFromServer.NpcWander(
                        type='npc_wander',
                        npc_ref_id=data.initiator.ref_id,
                        range=Distance.from_meters_to_ingame(30)
                    ))

                if say_ctx is not None:
                    if data.type == 'change_disposition':
                        if data.target.type == 'player':
                            d = "ей" if say_ctx.say_data.speaker.female else "ему"
                            n = "она" if say_ctx.say_data.speaker.female else "он"

                            for reason in data.reasons:
                                s = ""
                                match reason:
                                    case "trigger_like_conversation":
                                        s = f"{d} нравится наш разговор"
                                    case "trigger_dislike_conversation":
                                        s = f"{d} не нравится наш разговор"
                                    case "trigger_stop_conversation":
                                        s = f"{n} хочет закончить беседу"

                                    case "trigger_like_flatter":
                                        s = f"{d} нравится лесть"
                                    case "trigger_dislike_flatter":
                                        s = f"{d} не нравится лесть"

                                    case "trigger_threat":
                                        s = f"{n} чувствует угрозу"
                                    case "trigger_taunt":
                                        s = f"{n} чувствует насмешку"
                                    case "trigger_insult":
                                        s = f"{n} чувствует оскорбление"

                                    case "trigger_respect":
                                        s = f"{n} стал уважать меня больше"
                                    case "trigger_disrespect":
                                        s = f"{n} стал уважать меня меньше"

                                    case "trigger_accept_apology":
                                        s = f"{n} принимает мое извинение"
                                    case "trigger_reject_apology":
                                        s = f"{n} не принимает мое извинение"
                                    case "trigger_attack_PlayerSaveGame":
                                        s = f"{n} бросается на меня в атаку"
                                    case _:
                                        s = reason

                                if len(s) > 0:
                                    say_ctx.reaction_list.append(s)


                            say_ctx.reaction_list.append(
                                self._i18n.npc_change_disposition(data.value)
                            )

                            event_data_to_send.append(EventDataFromServer.ChangeDisposition(
                                type='change_disposition',
                                npc_ref_id=data.initiator.ref_id,
                                value=data.value
                            ))
                    elif data.type == 'npc_start_follow':
                        say_ctx.reaction_list.append(
                            self._i18n.npc_start_follow(
                                me=say_ctx.say_data.speaker,
                                follower=data.initiator,
                                target=data.target,
                            )
                        )
                        event_data_to_send.append(EventDataFromServer.NpcFollow(
                            type='npc_follow',
                            duration_hours=data.duration_hours,
                            npc_ref_id=data.initiator.ref_id,
                            target_ref_id=data.target.ref_id
                        ))
                    elif data.type == 'npc_stop_follow':
                        say_ctx.reaction_list.append(
                            self._i18n.npc_stop_follow(
                                me=say_ctx.say_data.speaker,
                                follower=data.initiator,
                                target=data.target,
                            )
                        )
            except:
                logger.error(f"Failed processing item data: {data}")

        if say_ctx:
            flushed_say_ctx.append(say_ctx)

        for say_ctx in flushed_say_ctx:
            reaction_text: str | None = None
            if len(say_ctx.reaction_list) > 0:
                reaction_text = ", ".join(say_ctx.reaction_list)

            text = say_ctx.say_data.text
            if say_ctx.say_data.target:
                t = say_ctx.say_data.target
                if t.type == 'npc':
                    text = f"{say_ctx.say_data.speaker.name} говорит {t.name}: {say_ctx.say_data.text}"
                else:
                    text = f"{say_ctx.say_data.speaker.name} говорит мне: {say_ctx.say_data.text}"
            else:
                text = f"{say_ctx.say_data.speaker.name} думает вслух: {say_ctx.say_data.text}"

            event_data_to_send.append(EventDataFromServer.ActorSays(
                type='actor_says',
                speaker_ref=say_ctx.say_data.speaker,
                target_ref=say_ctx.say_data.target,
                text=text,
                reaction_text=reaction_text,
                audio_duration_sec=say_ctx.say_data.audio_duration_sec
            ))

        for data in event_data_to_send:
            self._producer.produce_event(Event(data=data))

    async def _is_female(self, actor_ref: ActorRef) -> bool:
        if actor_ref.type == 'player':
            return self._player_provider.local_player.player_data.female
        elif actor_ref.type == 'npc':
            data = await self._npc_service.get_npc(actor_ref.ref_id)
            return data.npc_data.female
        else:
            return False
