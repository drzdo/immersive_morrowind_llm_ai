import asyncio
from util.logger import Logger
from typing import Any

from google.generativeai import GenerationConfig  # type: ignore
from google.generativeai.client import configure  # type: ignore
from google.generativeai.generative_models import GenerativeModel  # type: ignore
from pydantic import BaseModel
from llm.backend.abstract import AbstractLlmBackend, LlmBackendRequest, LlmBackendResponse

logger = Logger(__name__)


class GoogleLlmBackend(AbstractLlmBackend):
    class Config(BaseModel):
        api_key: str
        model_name: str

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._lock = asyncio.Lock()

        configure(api_key=self._config.api_key)

    async def send(self, request: LlmBackendRequest) -> LlmBackendResponse:
        await self._lock.acquire()
        try:
            self._model = GenerativeModel(
                model_name=self._config.model_name,
                system_instruction=request.system_instructions
            )

            history: list[Any] = []
            for m in request.history:
                role = "user"
                if m.role == 'user':
                    role = "user"
                elif m.role == 'model':
                    role = "model"
                else:
                    raise Exception(f"Unknown role '{m.role}'")

                history.append({
                    "role": role,
                    "parts": m.text
                })

            self._chat_session = self._model.start_chat(history=history)

            generation_config = GenerationConfig(
                max_output_tokens=1000,
                temperature=0.5,
                top_p=0.9,
                top_k=100
            )

            response = await self._chat_session.send_message_async(  # type: ignore
                request.text,
                generation_config=generation_config
            )

            return LlmBackendResponse(
                text=response.text.strip()
            )
        finally:
            self._lock.release()
