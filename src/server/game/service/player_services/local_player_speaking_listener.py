from typing import Any, Callable, Coroutine, Optional
from eventbus.data.actor_ref import ActorRef
from eventbus.event import Event
from eventbus.event_consumer import EventConsumer
from game.data.player_ref_looked_at import PlayerRefLookedAt
from util.now_ms import now_ms


class LocalPlayerSpeakingListener:
    def __init__(self, event_consumer: EventConsumer, callback: Callable[[str], Coroutine[Any, Any, None]]) -> None:
        self._callback = callback
        self._player_started_speaking_looking_at: Optional[ActorRef] = None
        self._player_stopped_speaking_looking_at: Optional[ActorRef] = None
        self._player_last_ref_looked_at: Optional[PlayerRefLookedAt] = None
        event_consumer.register_handler(self._handle_event)

    @property
    def player_started_speaking_looking_at(self):
        return self._player_started_speaking_looking_at

    @property
    def player_stopped_speaking_looking_at(self):
        return self._player_stopped_speaking_looking_at

    @property
    def player_last_ref_looked_at(self):
        return self._player_last_ref_looked_at

    async def _handle_event(self, event: Event):
        if event.data.type == 'dialog_text_submit':
            self._player_started_speaking_looking_at = event.data.actor_ref
            await self._handle_player_saying_something_to_target(event.data.text)
        elif event.data.type == 'stt_recognition_complete':
            await self._handle_player_saying_something_to_target(event.data.text)
        elif event.data.type == 'player_starts_speaking_looking_at':
            self._player_started_speaking_looking_at = event.data.actor_ref
        elif event.data.type == 'player_stops_speaking_looking_at':
            self._player_stopped_speaking_looking_at = event.data.actor_ref
        elif event.data.type == 'show_tooltip_for_ref':
            self._player_last_ref_looked_at = PlayerRefLookedAt(
                ref_id=event.data.ref_id,
                object_type=event.data.object_type,
                name=event.data.name,
                position=event.data.position,
                owner=event.data.owner,
                last_update_ms=now_ms()
            )

    async def _handle_player_saying_something_to_target(self, text: str):
        await self._callback(text)
