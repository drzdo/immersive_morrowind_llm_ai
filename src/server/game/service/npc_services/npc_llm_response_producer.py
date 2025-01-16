import asyncio
import json
import time
from typing import NamedTuple, Optional

from pydantic import BaseModel
from game.data.npc import Npc
from game.data.player_ref_looked_at import PlayerRefLookedAt
from game.data.story_item import StoryItem, StoryItemDataAlias, StoryItemData
from game.i18n.i18n import I18n
from game.service.npc_services.npc_llm_message_history_builder import NpcLlmMessageHistoryBuilder
from game.service.npc_services.npc_llm_system_instructions_builder import NpcLlmSystemInstructionsBuilder
from game.service.providers.env_provider import EnvProvider
from llm.message import LlmMessage
from llm.system import LlmSystem
from util.logger import Logger

logger = Logger(__name__)


class NpcLlmResponseProducer:
    class Request(NamedTuple):
        npc: Npc
        other_hearing_npcs: list[Npc]
        processed_items: list[StoryItem]
        unprocessed_items: list[StoryItem]
        reasoning: str
        player_ref_looked_at: Optional[PlayerRefLookedAt]

    class Response(NamedTuple):
        new_item_data_list: list[StoryItemDataAlias]
        raw_text: str

    class _RequestPreparedForReset(NamedTuple):
        llm_system_instructions: str
        llm_history_messages: list[LlmMessage]
        llm_message_to_send: str

    class _LogContext(BaseModel):
        npc: Npc
        hearing_npcs: list[Npc]
        unprocessed_items: list[StoryItem]

    def __init__(self, llm_system: LlmSystem, env_provider: EnvProvider,
                 system_instructions_builder: NpcLlmSystemInstructionsBuilder, i18n: I18n) -> None:
        self._llm_system = llm_system
        self._env_provider = env_provider
        self._system_instructions_builder = system_instructions_builder
        self._i18n = i18n

        self._main_session = llm_system.create_session()
        self._main_session_lock = asyncio.Lock()

    async def produce_npc_response(self, request: Request) -> Response:
        await self._main_session_lock.acquire()
        try:
            preprocessed_request = self._prepare_data_for_llm_reset(request)
            self._main_session.reset(
                system_instructions=preprocessed_request.llm_system_instructions,
                messages=preprocessed_request.llm_history_messages
            )

            log_context_model = NpcLlmResponseProducer._LogContext(
                hearing_npcs=request.other_hearing_npcs,
                npc=request.npc,
                unprocessed_items=request.unprocessed_items
            )
            log_context = json.dumps(log_context_model.model_dump(mode='json'), ensure_ascii=False)

            logger.info("Sent request to LLM, waiting...")
            t0 = time.time()
            raw_text = await self._main_session.send_message(
                user_text=preprocessed_request.llm_message_to_send,
                log_name=request.npc.actor_ref.ref_id,
                log_context=log_context
            )
            logger.info(f"Got response from LLM in {time.time() - t0} sec")
            processed_text = self._post_process_response_text(raw_text)

            new_item_data_list: list[StoryItemDataAlias] = [
                StoryItemData.SayRaw(
                    type='say_raw',
                    text=processed_text,
                    speaker=request.npc.actor_ref,
                    target=None
                )
            ]

            return NpcLlmResponseProducer.Response(new_item_data_list, processed_text)
        finally:
            self._main_session_lock.release()

    def _prepare_data_for_llm_reset(self, request: Request) -> _RequestPreparedForReset:
        history_builder = NpcLlmMessageHistoryBuilder(
            self._env_provider.now().game_time, request.npc.actor_ref, self._i18n)

        for item in request.processed_items:
            history_builder.add_story_item('npc_story', item)
        for item in request.unprocessed_items:
            history_builder.add_story_item('npc_story', item)

        # message = "(выбери одного из персонажей, кому хочешь ответить - и ответь)"
        message = f"({request.reasoning})"

        return NpcLlmResponseProducer._RequestPreparedForReset(
            llm_system_instructions=self._system_instructions_builder.build(
                request.npc, request.other_hearing_npcs, history_builder.build_history()),
            # llm_history_messages=history_builder.build_history(),
            llm_history_messages=[],
            llm_message_to_send=message
        )

    def _post_process_response_text(self, text_raw: str):
        text = text_raw.strip()

        # if text.startswith("("):
        #     til = text.find(")")
        #     if til > 0:
        #         text = text[til+1:]
        # text = text.strip()

        return text
