from abc import ABC, abstractmethod

from pydantic import BaseModel
from llm.message import LlmMessage


class LlmBackendRequest(BaseModel):
    system_instructions: str
    history: list[LlmMessage]
    text: str


class LlmBackendResponse(BaseModel):
    text: str


class AbstractLlmBackend(ABC):
    @abstractmethod
    async def send(self, request: LlmBackendRequest) -> LlmBackendResponse:
        pass
