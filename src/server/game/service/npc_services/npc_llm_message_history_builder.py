from typing import Literal, NamedTuple
from eventbus.data.actor_ref import ActorRef
from game.data.story_item import StoryItem
from game.data.time import GameTime
from game.i18n.i18n import I18n
from game.service.story_item.npc_story_item_helper import NpcStoryItemHelper
from game.service.story_item.story_item_to_history import StoryItemToHistoryConverter
from llm.message import LlmMessage
from util.logger import Logger

logger = Logger(__name__)


class NpcLlmMessageHistoryBuilder:
    class _Accumulator(NamedTuple):
        is_from_npc: bool
        lines: list[str]

    def __init__(self, now: GameTime, actor: ActorRef | None, i18n: I18n):
        self._now = now
        self._actor = actor
        self._i18n = i18n

        self._flushed_messages: list[LlmMessage] = []
        self._accumulator: NpcLlmMessageHistoryBuilder._Accumulator | None = None

        self._last_speaker_to_npc: ActorRef | None = None

    def add_story_item(self, pov: Literal['npc_story', 'pick_actor'], item: StoryItem):
        is_from_npc = NpcStoryItemHelper.is_actor_is_initiator(self._actor, item.data) if self._actor else False

        if self._accumulator is not None and self._accumulator.is_from_npc != is_from_npc:
            self._flush()
        if self._accumulator is None:
            self._accumulator = NpcLlmMessageHistoryBuilder._Accumulator(
                is_from_npc=is_from_npc,
                lines=[]
            )

        delta_sec = self._now.to_unix_timestamp_sec() - item.time.game_time.to_unix_timestamp_sec()
        delta_sec = max(delta_sec, 0)

        line = StoryItemToHistoryConverter.convert_item_to_line(pov, self._actor, item.data, delta_sec)
        line = line.strip()
        if len(line) > 0:
            self._accumulator.lines.append(line)

    def build_history(self) -> list[LlmMessage]:
        self._flush()
        return self._flushed_messages.copy()

    def get_last_speaker_to_npc(self) -> ActorRef | None:
        return self._last_speaker_to_npc

    def _flush(self):
        if self._accumulator is None:
            return

        if len(self._accumulator.lines) > 0:
            message = LlmMessage(
                role='model' if self._accumulator.is_from_npc else 'user',
                text="\n".join(self._accumulator.lines)
            )
            self._flushed_messages.append(message)
        else:
            logger.error(f"Accumulator was flushed with 0 lines: npc={self._actor}")

        self._accumulator = None
