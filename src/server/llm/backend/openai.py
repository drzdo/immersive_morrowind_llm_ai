import asyncio
import time
from typing import Any
from util.logger import Logger

from google.generativeai.client import configure  # type: ignore
from google.generativeai.generative_models import GenerativeModel  # type: ignore
from pydantic import BaseModel, Field
from llm.backend.abstract import AbstractLlmBackend, LlmBackendRequest, LlmBackendResponse

from openai import OpenAI

logger = Logger(__name__)


class OpenAiLlmBackend(AbstractLlmBackend):
    class Config(BaseModel):
        base_url: str
        api_key: str
        model_name: str

        system_instructions_role: str = Field(default='system')
        max_tokens: int = Field(default=1024)
        temperature: float = Field(default=0.7)

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._lock = asyncio.Lock()

        self._client = OpenAI(api_key=self._config.api_key, base_url=self._config.base_url)

    async def send(self, request: LlmBackendRequest) -> LlmBackendResponse:
        await self._lock.acquire()
        try:
            history: list[Any] = []

            if len(request.system_instructions) > 0:
                history.append({
                    "role": self._config.system_instructions_role,
                    "content": request.system_instructions
                })

            for m in request.history:
                role = "user"
                if m.role == 'user':
                    role = "user"
                elif m.role == 'model':
                    role = "assistant"
                else:
                    raise Exception(f"Unknown role '{m.role}'")

                history.append({
                    "role": role,
                    "content": m.text
                })

            t0 = time.time()
            logger.debug("Sent request to the model, waiting...")
            response = self._client.chat.completions.create(
                model=self._config.model_name,
                messages=history,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                stream=False,
            )
            dt = time.time() - t0
            logger.debug(f"Response from the model received in {dt} sec")
            logger.debug(f"> {response}")

            text = response.choices[0].message.content
            if text:
                text = text.strip()
            else:
                logger.warning(f"Received empty response from the model: {response}")
                text = ''

            return LlmBackendResponse(
                text=text
            )
        finally:
            self._lock.release()
