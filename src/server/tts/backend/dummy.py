from tts.backend.abstract import AbstractTtsBackend, TtsBackendRequest, TtsBackendResponse


class DummyTtsBackend(AbstractTtsBackend):
    async def convert(self, request: TtsBackendRequest) -> TtsBackendResponse | None:
        return None
