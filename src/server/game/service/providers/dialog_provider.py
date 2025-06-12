from typing import Callable, Optional
from eventbus.data.actor_ref import ActorRef
from eventbus.data.topic_data import TopicData
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
# from game.data.story import Story
# from game.service.npc_services.npc_service import NpcService
# from game.service.player_services.player_provider import PlayerProvider


class DialogProvider:
    def __init__(self, consumer: EventConsumer):  # , player_provider: PlayerProvider, npc_provider: NpcService)
        # self._player_provider = player_provider
        # self._npc_provider = npc_provider

        self.topics: list[TopicData] = []
        self.is_in_dialog = False
        self.npc_ref: Optional[ActorRef] = None

        self.on_topic_story_item_update: Callable[[ActorRef], None] | None = None

        consumer.register_handler(self._handle_event)

    async def _handle_event(self, event: Event):
        if event.data.type == 'dialog_close':
            self.is_in_dialog = False
        elif event.data.type in ['dialog_open', 'dialog_update']:
            self.is_in_dialog = True
            self.topics = event.data.topics
            self.npc_ref = event.data.npc_ref
        elif event.data.type == 'get_local_player_response':
            self.is_in_dialog = event.data.player_data.in_dialog

    # def _update_story_if_needed(self, actor: ActorRef, story: Story):
    #     is_story_changed = False
    #     if len(story.items) > 0:
    #         item = story.items[-1]
    #         if item.data.type == 'player_trigger_dialog_topic' and len(item.data.topic_text) == 0:
    #             for topic in self.topics:
    #                 if topic.topic_text == item.data.trigger_topic:
    #                     item.data.topic_text = topic.topic_response
    #                     is_story_changed = True
    #                     break

    #     if is_story_changed and self.on_topic_story_item_update:
    #         self.on_topic_story_item_update(self._player_provider.local_player.actor_ref)
