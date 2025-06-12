from eventbus.data.actor_ref import ActorRef
from game.data.player import Player
from game.data.player_ref_looked_at import PlayerRefLookedAt
from game.service.npc_services.npc_llm_pick_actor_service import NpcLlmPickActorService
from game.service.providers.dialog_provider import DialogProvider
from util.logger import Logger
from typing import NamedTuple, Optional
from eventbus.data.topic_data import TopicData
from game.data.npc import Npc
from game.data.story_item import StoryItem, StoryItemData, StoryItemDataAlias
from game.service.providers.env_provider import EnvProvider
from game.service.npc_services.npc_llm_response_producer import NpcLlmResponseProducer
from game.service.story_item.npc_story_item_helper import NpcStoryItemHelper

logger = Logger(__name__)


class NpcBehaviorService:
    class Request(NamedTuple):
        npc: Npc
        other_hearing_npcs: list[Npc]
        is_in_dialog: bool
        known_topics: list[TopicData]
        reasoning: str
        player_ref_looked_at: Optional[PlayerRefLookedAt]

    class Response(NamedTuple):
        item_data_list: list[StoryItemDataAlias]
        is_behavior_updated: bool

    def __init__(self, max_used_in_llm_story_items: int, env_provider: EnvProvider,
                 pick_actor_service: NpcLlmPickActorService, npc_llm_response_producer: NpcLlmResponseProducer,
                 dialog_provider: DialogProvider) -> None:
        self._max_used_in_llm_story_items = max_used_in_llm_story_items
        self._env_provider = env_provider
        self._pick_actor_service = pick_actor_service
        self._npc_llm_response_producer = npc_llm_response_producer
        self._dialog_provider = dialog_provider

        self._common_topics_lowercased: list[str] = list(map(lambda s: s.lower(), [
            "мое занятие", "Мудрость Морровинда", "Услуги", "кто-то особенный", "маленький секрет",
            "небольшой совет", "определенное место", "свежие сплетни", "Биография"
        ]))


    async def decide_who_should_act(self, player: Player, target: Optional[ActorRef], npcs: list[Npc]) -> NpcLlmPickActorService.Response:
        if not npcs:
            logger.debug("No NPCs are passed, picking player to act")
            return NpcLlmPickActorService.Response(player.actor_ref, "(no npcs are passed)", pass_reason_to_npc=False)

        story_items_from_npc = npcs[0].personal_story.items[-self._max_used_in_llm_story_items:]

        npc_actors = list(map(lambda n: n.actor_ref, npcs))
        story_items_from_director = list(
            filter(lambda i: i.data.type == 'actor_pick_reason' and i.data.actor in npc_actors, player.personal_story.items)
        )[-self._max_used_in_llm_story_items:]

        #
        story_items = story_items_from_npc.copy()
        story_items.extend(story_items_from_director)
        story_items.sort(key=lambda i: i.time)

        if len(story_items) > 0:
            last_item = story_items[-1]
            if last_item.data.type == 'player_trigger_dialog_topic':
                return NpcLlmPickActorService.Response(
                    last_item.data.target,
                    f"Topic '{last_item.data.trigger_topic}' triggered",
                    pass_reason_to_npc=False
                )
            elif last_item.data.type == 'player_trigger_list_dialog_topics':
                return NpcLlmPickActorService.Response(
                    last_item.data.target,
                    "List of topics triggered",
                    pass_reason_to_npc=False,
                )


        request = NpcLlmPickActorService.Request(player, hearing_npcs=npcs, story_items=story_items, target=target,
                                                 is_in_dialog=self._dialog_provider.is_in_dialog)
        response = await self._pick_actor_service.pick_npc_to_act(request)
        logger.debug(f"Pick response: {response}")
        return response

    async def decide_how_npc_should_act(self, request: Request) -> Response:
        return await self._process_reactive_behavior(request)

    async def _process_reactive_behavior(self, request: Request) -> Response:
        npc = request.npc

        (processed, unprocessed) = self._split_items_by_being_processed_status(npc)

        # Process dialog topic trigger.
        for item in unprocessed:
            if (
                item.data.type == 'player_trigger_dialog_topic' and
                request.is_in_dialog and
                item.data.target == npc.actor_ref
            ):
                logger.debug(f"Npc {npc.actor_ref.ref_id} has triggered topic {item.data.trigger_topic}")

                topic_response = next(
                    (
                        known_topic.topic_response
                        for known_topic in request.known_topics
                        if known_topic.topic_text == item.data.trigger_topic
                    ),
                    "...",
                )
                return NpcBehaviorService.Response(
                    item_data_list=[
                        StoryItemData.NpcTriggerDialogTopic(
                            type='npc_trigger_dialog_topic',
                            speaker=npc.actor_ref,
                            target=item.data.speaker,
                            topic_name=item.data.trigger_topic,
                            topic_response=topic_response
                        )
                    ],
                    is_behavior_updated=True
                )

            if (
                item.data.type == 'player_trigger_list_dialog_topics' and
                item.data.target == npc.actor_ref
            ):
                logger.debug(f"Npc {npc.actor_ref.ref_id} has triggered list of topic")

                topics: list[str] = []
                topics.extend(
                    known_topic.topic_text
                    for known_topic in request.known_topics
                    if known_topic.topic_text.lower()
                    not in self._common_topics_lowercased
                )
                if topics:
                    return NpcBehaviorService.Response(
                        item_data_list=[
                            StoryItemData.SayProcessed(
                                type='say_processed',
                                speaker=npc.actor_ref,
                                target=item.data.speaker,
                                text=f"Мы можем предметно поговорить о {", ".join(topics)}"
                            )
                        ],
                        is_behavior_updated=True
                    )
                else:
                    return NpcBehaviorService.Response(
                        item_data_list=[
                            StoryItemData.SayProcessed(
                                type='say_processed',
                                speaker=npc.actor_ref,
                                target=item.data.speaker,
                                text="Нам с тобой не о чем предметно разговаривать"
                            )
                        ],
                        is_behavior_updated=True
                    )


        # Run LLM to generate a response.
        logger.debug(f"Npc {npc.actor_ref.ref_id} has {len(unprocessed)} unprocessed items, will be processing him")
        logger.debug(f"unprocessed: {unprocessed}")
        llm_request = NpcLlmResponseProducer.Request(
            npc=npc,
            other_hearing_npcs=request.other_hearing_npcs,
            processed_items=processed,
            unprocessed_items=unprocessed,
            reasoning=request.reasoning,
            player_ref_looked_at=request.player_ref_looked_at
        )
        llm_response = await self._npc_llm_response_producer.produce_npc_response(llm_request)

        if len(unprocessed) > 0:
            npc.behavior.last_processed_story_item_id = unprocessed[-1].item_id

        return NpcBehaviorService.Response(
            item_data_list=llm_response.new_item_data_list,
            is_behavior_updated=True
        )

    def _split_items_by_being_processed_status(self, npc: Npc) -> tuple[list[StoryItem], list[StoryItem]]:
        items_to_use_in_llm = npc.personal_story.items[-self._max_used_in_llm_story_items:]

        if npc.behavior.last_processed_story_item_id is None:
            return ([], items_to_use_in_llm)

        processed_items: list[StoryItem] = []
        unprocessed_items: list[StoryItem] = []

        for item in items_to_use_in_llm:
            if item.item_id > npc.behavior.last_processed_story_item_id:
                unprocessed_items.append(item)
            else:
                processed_items.append(item)

        return (processed_items, unprocessed_items)

    def _get_items_where_npc_is_target(self, npc: Npc, items: list[StoryItem]) -> list[StoryItem]:
        def filter_item(item: StoryItem) -> bool:
            return NpcStoryItemHelper.is_actor_is_target(npc.actor_ref, item.data)

        return list(filter(filter_item, items))
