from llm.backend.abstract import AbstractLlmBackend, LlmBackendRequest, LlmBackendResponse

class DummyLlmBackend(AbstractLlmBackend):
    async def send(self, request: LlmBackendRequest) -> LlmBackendResponse:
        return LlmBackendResponse(text="Hello, I am dummy LLM emulator.")
