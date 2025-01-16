from llm.llm_logger import LlmLogger
from util.logger import Logger
from llm.backend.abstract import AbstractLlmBackend, LlmBackendRequest
from llm.message import LlmMessage

logger = Logger(__name__)


class LlmSession:
    def __init__(self, backend: AbstractLlmBackend, llm_logger: LlmLogger | None) -> None:
        self._backend = backend
        self._llm_logger = llm_logger

        self._system_instructions = ''
        self._messages: list[LlmMessage] = []

    def reset(self, *, system_instructions: str, messages: list[LlmMessage]):
        self._system_instructions = system_instructions
        self._messages = messages

    async def send_message(self, *, user_text: str, log_name: str | None = None, log_context: str | None = None) -> str:
        request = LlmBackendRequest(
            system_instructions=self._system_instructions,
            history=self._messages,
            text=user_text
        )

        logger.debug(f"[SYSTEM:0] {self._system_instructions}")
        message_index = 1
        for m in self._messages:
            if m.role == 'user':
                logger.debug(f"[USER:{message_index}] {m.text}")
            else:
                logger.debug(f"[MODEL:{message_index}] {m.text}")
            message_index = message_index + 1

        logger.info(f"< {user_text}")
        response = await self._backend.send(request)
        logger.info(f"> {response.text}")

        if self._llm_logger:
            self._llm_logger.log(
                system_instructions=self._system_instructions,
                history=self._messages,
                user_message=user_text,
                model_response=response.text,
                log_name=log_name,
                log_context=log_context
            )

        self._messages.append(LlmMessage(role='user', text=user_text))
        self._messages.append(LlmMessage(role='model', text=response.text))

        return response.text
