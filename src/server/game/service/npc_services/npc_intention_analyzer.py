import random
from typing import Optional

from eventbus.data.actor_ref import ActorRef
from game.data.npc import Npc
from game.data.story_item import StoryItemData, StoryItemDataAlias
from game.service.npc_services.npc_service import NpcService
from game.service.npc_services.npc_spawn_list import NPC_SPAWN_LIST
from game.service.player_services.player_provider import PlayerProvider
from game.service.providers.dropped_items_provider import DroppedItemsProvider
from game.service.scene.scene_instructions import SceneInstructions
from game.service.util.text_sanitizer import TextSanitizer
from util.logger import Logger


logger = Logger(__name__)

class NpcIntentionAnalyzer:
    def __init__(self, player_provider: PlayerProvider, npc_service: NpcService, text_sanitizer: TextSanitizer, dropped_item_provider: DroppedItemsProvider,
                 scene_instructions: SceneInstructions):
        self._player_provider = player_provider
        self._npc_service = npc_service
        self._text_sanitizer = text_sanitizer
        self._dropped_item_provider = dropped_item_provider
        self._scene_instructions = scene_instructions

        self._emotional_triggers: dict[str, int] = {
            "trigger_like_conversation": +5,
            "trigger_dislike_conversation": -5,
            "trigger_stop_conversation": -10,

            "trigger_like_flatter": +5,
            "trigger_dislike_flatter": -5,

            "trigger_threat": -5,
            "trigger_taunt": -5,
            "trigger_insult": -5,

            "trigger_respect": 5,
            "trigger_disrespect": -5,

            "trigger_accept_apology": 2,
            "trigger_reject_apology": -2,
        }

    async def process_story_item_data(self, npcs: list[Npc], item_data: StoryItemDataAlias) -> list[StoryItemDataAlias]:
        if item_data.type == 'say_raw' and item_data.speaker.type == 'npc':
            npc_speaker = await self._npc_service.get_npc(item_data.speaker.ref_id)
            new_list = await self._determine_story_item_data_from_npc_saying(npcs, npc_speaker, item_data.text, item_data.target)
            return new_list

        return [item_data]

    async def _determine_story_item_data_from_npc_saying(self, npcs: list[Npc], speaker_npc: Npc, text_raw: str, target_ref: Optional[ActorRef]) -> list[StoryItemDataAlias]:
        text = self._text_sanitizer.sanitize(text_raw)

        logger.debug(f"Analyzying NPC intention in '{text}'")
        result: list[StoryItemDataAlias] = []
        accumulated_disposition_change = 0
        accumulated_change_disposition_reasons: list[str] = []

        #
        text, disposition_change, change_disposition_reasons = self._process_emotional_triggers(text)
        accumulated_disposition_change = accumulated_disposition_change + disposition_change
        accumulated_change_disposition_reasons.extend(change_disposition_reasons)

        #
        text, target_ref = await self._process_text_and_determine_target(text, npcs)

        #
        text, disposition_change, change_disposition_reasons, data_list_wip = self._process_triggers_which_require_target(
            text, speaker_npc.actor_ref, target_ref)
        accumulated_disposition_change = accumulated_disposition_change + disposition_change
        accumulated_change_disposition_reasons.extend(change_disposition_reasons)
        result.extend(data_list_wip)

        #
        text, data_list_wip = self._process_trigger_attack(text, speaker_npc.actor_ref, npcs)
        result.extend(data_list_wip)

        #
        text, data_list_wip = self._process_trigger_come(text, speaker_npc.actor_ref, npcs)
        if len(data_list_wip) > 0:
            result.extend(data_list_wip)
        elif random.random() < 0.85 and target_ref:
            result.append(StoryItemData.NpcCome(
                type='npc_come',
                initiator=speaker_npc.actor_ref,
                target=target_ref
            ))

        #
        text, data_list_wip = self._process_trigger_poi(text, speaker_npc.actor_ref, npcs)
        result.extend(data_list_wip)

        #
        text, data_list_wip = self._process_item_drop(text, speaker_npc.actor_ref)
        result.extend(data_list_wip)

        # If there is npc_start_follow, there should be no npc_come as latter aborts the first.
        has_npc_start_follow = False
        for item in result:
            if item.type == 'npc_start_follow':
                has_npc_start_follow = True
                break
        if has_npc_start_follow:
            i = 0
            while i < len(result):
                item = result[i]
                if item.type == 'npc_come':
                    logger.debug("Dropped npc_come due to npc_start_follow")
                    result.pop(i)
                    i = i - 1
                i = i + 1

        # Build final list.
        text = self._text_sanitizer.sanitize(text)

        result.insert(0, StoryItemData.SayProcessed(
            type='say_processed',
            speaker=speaker_npc.actor_ref,
            target=target_ref,
            text=text,
            audio_duration_sec=None
        ))

        if accumulated_disposition_change != 0 and target_ref:
            result.append(
                StoryItemData.ChangeDisposition(
                    type='change_disposition',
                    initiator=speaker_npc.actor_ref,
                    target=target_ref,
                    value=accumulated_disposition_change,
                    reasons=accumulated_change_disposition_reasons
                )
            )

        return result

    def _process_emotional_triggers(self, text: str):
        disposition_change = 0
        change_disposition_reasons: list[str] = []

        for trigger in self._emotional_triggers:
            if self._has_trigger(trigger=trigger, text=text):
                text = self._delete_trigger_from_text(text=text, trigger=trigger)
                change_disposition_reasons.append(trigger)

                disposition_change_range = self._emotional_triggers[trigger]
                if disposition_change_range != 0:
                    change = random.randint(1, abs(disposition_change_range))
                    if disposition_change_range < 0:
                        change = -change
                    disposition_change = disposition_change + change

        return (text, disposition_change, change_disposition_reasons)

    async def _process_text_and_determine_target(self, text: str, npcs: list[Npc]):
        result: ActorRef | None = None

        if result is None:
            text, targets_wip = self._process_trigger_answer(text, npcs)
            result = targets_wip[0] if len(targets_wip) > 0 else None

        if result is None:
            target_wip = self._determine_target_name_from_prefix_with_name(text, npcs)
            result = target_wip

        if result is None:
            target_wip = await self._determine_target_ref_id_from_prefix_with_name_ref(text)
            result = target_wip

        text = self._clean_target_prefix(text)
        text = self._clean_left_trigger_answer(text)

        return (text, result)

    def _process_item_drop(self, text: str, speaker: ActorRef):
        result: list[StoryItemDataAlias] = []

        for spawn_item in NPC_SPAWN_LIST:
            i0 = text.lower().find(spawn_item.trigger)
            if i0 >= 0:
                count = 1

                i1 = i0 + len(spawn_item.trigger)
                if i1 < len(text) and text[i1] == "[":
                    i2 = text.find("]", i1 + 1)
                    if i2 >= 0:
                        count = int(text[i1 + 1:i2])
                        i1 = i2 + 1

                trigger_full = text[i0:i1]
                text = self._delete_trigger_from_text(text=text, trigger=trigger_full)

                result.append(StoryItemData.NpcDropItem(
                    type='npc_drop_item',
                    initiator=speaker,
                    item_id=spawn_item.item_id,
                    item_name=spawn_item.item_name,
                    count=count,
                    water_amount=random.randint(1, spawn_item.water_amount) if spawn_item.water_amount else None
                ))

        return (text, result)

    def _process_triggers_which_require_target(self, text: str, speaker: ActorRef, target_ref: Optional[ActorRef]):
        result: list[StoryItemDataAlias] = []
        disposition_change = 0
        change_disposition_reasons: list[str] = []

        if self._has_trigger(trigger="trigger_attack_PlayerSaveGame", text=text):
            text = self._delete_trigger_from_text(text=text, trigger="trigger_attack_PlayerSaveGame")
            result.append(StoryItemData.NpcAttack(
                type='npc_attack',
                initiator=speaker,
                victim=self._player_provider.local_player.actor_ref
            ))
            disposition_change = disposition_change - 100
            change_disposition_reasons.append("trigger_attack_PlayerSaveGame")

        if self._has_trigger(trigger="trigger_start_follow", text=text):
            text = self._delete_trigger_from_text(text=text, trigger="trigger_start_follow")
            if target_ref:
                result.append(StoryItemData.NpcStartFollow(
                    type='npc_start_follow',
                    initiator=speaker,
                    target=target_ref,
                    duration_hours=None
                ))

        if "решил идти вместе" in text:
            result.append(StoryItemData.NpcStartFollow(
                type='npc_start_follow',
                initiator=speaker,
                target=self._player_provider.local_player.actor_ref,
                duration_hours=None
            ))

        if self._has_trigger(trigger="trigger_help", text=text):
            text = self._delete_trigger_from_text(text=text, trigger="trigger_help")
            if target_ref:
                result.append(StoryItemData.NpcStartFollow(
                    type='npc_start_follow',
                    initiator=speaker,
                    target=target_ref,
                    duration_hours=1
                ))

        if self._has_trigger(trigger="trigger_stop_follow", text=text):
            text = self._delete_trigger_from_text(text=text, trigger="trigger_stop_follow")
            if target_ref:
                result.append(StoryItemData.NpcStopFollow(
                    type='npc_stop_follow',
                    initiator=speaker,
                    target=target_ref
                ))

        if "решил больше не идти вместе" in text:
            result.append(StoryItemData.NpcStopFollow(
                type='npc_stop_follow',
                initiator=speaker,
                target=self._player_provider.local_player.actor_ref
            ))

        dropped_items_count = len(self._dropped_item_provider.dropped_items)
        for index in range(0, dropped_items_count):
            trigger = f"trigger_pick_up_item_{index}"
            if self._has_trigger(trigger=trigger, text=text):
                text = self._delete_trigger_from_text(text=text, trigger=trigger)

                dropped_item = self._dropped_item_provider.dropped_items[index]
                result.append(StoryItemData.NpcPickUpItem(
                    type='npc_pick_up_item',
                    initiator=speaker,
                    item_ref_id=dropped_item.ref_id,
                    item_name=dropped_item.name,
                    dropped_item_id=dropped_item.dropped_item_id
                ))

        return (text, disposition_change, change_disposition_reasons, result)

    def _process_trigger_attack(self, text: str, speaker: ActorRef, npcs: list[Npc]):
        result: list[StoryItemDataAlias] = []

        for other_npc in npcs:
            if other_npc.actor_ref == speaker:
                continue

            trigger = f"trigger_attack_{other_npc.actor_ref.ref_id}"
            if self._has_trigger(trigger=trigger, text=text):
                logger.debug(f"Attack trigger found {trigger}")
                result.append(StoryItemData.NpcAttack(
                    type='npc_attack',
                    initiator=speaker,
                    victim=other_npc.actor_ref
                ))
                text = self._delete_trigger_from_text(text=text, trigger=trigger)

        return (text, result)

    def _process_trigger_poi(self, text: str, speaker: ActorRef, npcs: list[Npc]):
        result: list[StoryItemDataAlias] = []

        poi_index = 0
        for poi in self._scene_instructions.pois:
            trigger = f"trigger_poi_{poi_index}"
            if self._has_trigger(trigger=trigger, text=text):
                text = self._delete_trigger_from_text(text=text, trigger=trigger)

                match poi.type:
                    case 'travel':
                        result.append(StoryItemData.NpcTravel(
                            type='npc_travel',
                            initiator=speaker,
                            destination=poi.pos
                        ))
                    case 'activate':
                        result.append(StoryItemData.NpcActivate(
                            type='npc_activate',
                            initiator=speaker,
                            target_ref_id=poi.ref_id,
                            target_position=poi.pos
                        ))

            poi_index = poi_index + 1
        return (text, result)

    def _process_trigger_come(self, text: str, speaker: ActorRef, npcs: list[Npc]):
        result: list[StoryItemDataAlias] = []

        if self._has_trigger(trigger="trigger_come_PlayerSaveGame", text=text):
            text = self._delete_trigger_from_text(text=text, trigger="trigger_come_PlayerSaveGame")
            result.append(StoryItemData.NpcCome(
                type='npc_come',
                initiator=speaker,
                target=self._player_provider.local_player.actor_ref
            ))

        found_trigger = False
        for other_npc in npcs:
            if other_npc.actor_ref == speaker:
                continue

            trigger = f"trigger_come_{other_npc.actor_ref.ref_id}"
            if self._has_trigger(trigger=trigger, text=text):
                text = self._delete_trigger_from_text(text=text, trigger=trigger)
                result.append(StoryItemData.NpcCome(
                    type='npc_come',
                    initiator=speaker,
                    target=other_npc.actor_ref
                ))
                found_trigger = True
                break

        if not found_trigger:
            for other_npc in npcs:
                if other_npc.actor_ref == speaker:
                    continue

                triggers = [
                    f"подходит ближе к {other_npc.actor_ref.name}",
                    f"подходит к {other_npc.actor_ref.name}"
                ]
                for trigger in triggers:
                    if trigger in text:
                        result.append(StoryItemData.NpcCome(
                            type='npc_come',
                            initiator=speaker,
                            target=other_npc.actor_ref
                        ))
                        found_trigger = True
                        break

        return (text, result)

    def _has_trigger(self, *, text: str, trigger: str):
        text_lc = text.lower()
        trigger_lc = trigger.lower()
        i0 = text_lc.find(trigger_lc)
        return i0 >= 0

    def _delete_trigger_from_text(self, *, text: str, trigger: str):
        text_lc = text.lower()
        trigger_lc = trigger.lower()
        i0 = text_lc.find(trigger_lc)
        if i0 >= 0:
            i1 = i0 + len(trigger_lc)
            text = text[:i0] + text[i1:]
            text = text.replace("  ", " ").strip()
        return text

    def _process_trigger_answer(self, text: str, npcs: list[Npc]) -> tuple[str, list[ActorRef]]:
        targets: list[ActorRef] = []

        trigger = f"trigger_answer_{self._player_provider.local_player.actor_ref.ref_id}"
        if self._has_trigger(trigger=trigger, text=text):
            text = self._delete_trigger_from_text(text=text, trigger=trigger)
            targets.append(self._player_provider.local_player.actor_ref)

        for other_npc in npcs:
            triggers = [
                f"trigger_answer_{other_npc.actor_ref.ref_id}",
                f"trigger_answer_{other_npc.actor_ref.ref_id}".replace("00000000", "")
            ]
            for trigger in triggers:
                if self._has_trigger(trigger=trigger, text=text):
                    logger.debug(f"Answer trigger found {trigger}")
                    text = self._delete_trigger_from_text(text=text, trigger=trigger)
                    targets.append(other_npc.actor_ref)
                    break

        return (text, targets)

    def _clean_left_trigger_answer(self, text: str):
        # Model may decide to respond to the absent NPC - remove that answer tag.
        i0 = text.lower().find("trigger_answer_")
        if i0 >= 0:
            ends = ["000000", " "]
            for end in ends:
                i1 = text.find(end, i0)
                if i1 >= 0:
                    i2 = text.find(" ", i1)
                    if i2 >= 0:
                        text = text[:i0] + text[i2:]
                        text = text.strip()
                        break

        return text

    def _determine_target_name_from_prefix_with_name(self, text: str, npcs: list[Npc]):
        # (Я сказала Губерон)
        i_said_index = text.find("(Я сказал")
        if i_said_index >= 0:
            i1 = text.find(")", i_said_index)
            if i1 >= 0:
                substr = text[i_said_index:i1]
                if self._player_provider.local_player.actor_ref.name in substr:
                    return self._player_provider.local_player.actor_ref
                else:
                    for npc in npcs:
                        if npc.actor_ref.name in substr:
                            return npc.actor_ref
        return None

    async def _determine_target_ref_id_from_prefix_with_name_ref(self, text: str):
        target_ref: ActorRef | None = None
        if text.startswith("("):
            i1 = text.find(")", 1)
            if i1 >= 0:
                i2 = text.rfind("|", 1, i1)
                if i2 >= 0:
                    target_ref_id_from_msg = text[i2 + 1:i1]
                    if target_ref_id_from_msg == self._player_provider.local_player.actor_ref.ref_id:
                        target_ref = self._player_provider.local_player.actor_ref
                    else:
                        try:
                            target_npc = await self._npc_service.get_npc(target_ref_id_from_msg)
                            target_ref = target_npc.actor_ref
                            logger.debug(f"Determined target {target_ref} from the message")
                        except:
                            logger.warning(
                                f"Couldn't find target with ref '{target_ref_id_from_msg}' from the last LLM response")
        return target_ref

    def _clean_target_prefix(self, text: str):
        if text.startswith("("):
            i1 = text.find(")", 1)
            if i1 >= 0:
                text = text[i1+1:]
        return text
