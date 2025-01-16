from llm.backend.anthropic import AnthropicLlmBackend
from llm.backend.mistral import MistralLlmBackend
from llm.backend.openai import OpenAiLlmBackend
from llm.llm_logger import LlmLogger
from util.logger import Logger
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field
from llm.backend.abstract import AbstractLlmBackend
from llm.backend.dummy import DummyLlmBackend
from llm.backend.google import GoogleLlmBackend
from llm.session import LlmSession
from util.colored_lines import green

logger = Logger(__name__)

class LlmSystem:
    class Config(BaseModel):
        class Dummy(BaseModel):
            type: Literal['dummy']

        class Google(BaseModel):
            type: Literal['google']
            google: GoogleLlmBackend.Config

        class OpenAi(BaseModel):
            type: Literal['openai']
            openai: OpenAiLlmBackend.Config

        class Mistral(BaseModel):
            type: Literal['mistral']
            mistral: MistralLlmBackend.Config

        class Anthropic(BaseModel):
            type: Literal['anthropic']
            anthropic: AnthropicLlmBackend.Config

        system: Union[Dummy, Google, OpenAi, Mistral, Anthropic] = Field(discriminator='type')
        llm_logger: Optional[LlmLogger.Config] = Field(default=None)

    def __init__(self, config: Config) -> None:
        self._config = config
        self._backend = self._create_backend()
        self._llm_logger = LlmLogger(config.llm_logger) if config.llm_logger else None

    def _create_backend(self) -> AbstractLlmBackend:
        backend: AbstractLlmBackend
        if self._config.system.type == 'dummy':
            logger.info(f"LLM system is set to {green('dummy')}")
            backend = DummyLlmBackend()
        elif self._config.system.type == 'google':
            logger.info(f"LLM system is set to {green('google')}")
            backend = GoogleLlmBackend(self._config.system.google)
        elif self._config.system.type == 'openai':
            logger.info(f"LLM system is set to {green('openai')}")
            backend = OpenAiLlmBackend(self._config.system.openai)
        elif self._config.system.type == 'mistral':
            logger.info(f"LLM system is set to {green('mistral')}")
            backend = MistralLlmBackend(self._config.system.mistral)
        elif self._config.system.type == 'anthropic':
            logger.info(f"LLM system is set to {green('anthropic')}")
            backend = AnthropicLlmBackend(self._config.system.anthropic)
        else:
            raise Exception(f"Unknown LLM system '{self._config.system}'")

        return backend

    def create_session(self):
        return LlmSession(self._backend, self._llm_logger)
