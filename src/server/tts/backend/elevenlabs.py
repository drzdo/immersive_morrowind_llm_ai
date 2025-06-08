import asyncio
from typing import Optional
from util.logger import Logger
from threading import Lock, Thread
import time

from pydantic import BaseModel
from tts.backend.abstract import AbstractTtsBackend, TtsBackendRequest, TtsBackendResponse

from elevenlabs import ElevenLabs,VoiceSettings,save

from tts.voice import Voice

logger = Logger(__name__)


class _Request(BaseModel):
    request_id: int
    text: str
    voice_id: str
    voice_settings: VoiceSettings
    file_path: str


class ElevenlabsTtsBackend(AbstractTtsBackend):
    class Config(BaseModel):
        class Voices(BaseModel):
            d_male: str
            n_male: str
            i_male: str
            h_male: str
            k_male: str
            b_male: str
            a_male: str
            o_male: str
            r_male: str
            w_male: str

            d_female: str
            n_female: str
            i_female: str
            h_female: str
            k_female: str
            b_female: str
            a_female: str
            o_female: str
            r_female: str
            w_female: str

            socucius: Optional[str]

        api_key: str
        model_id: str
        language_code: str
        max_wait_time_sec: float

        voices: Voices

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._elevenlabs = ElevenLabs(
            api_key=config.api_key,
        )
        self._model_id = config.model_id
        self._language_code = config.language_code

        self._max_wait_time_sec = config.max_wait_time_sec

        self._requests_lock = Lock()
        self._requests: list[_Request] = []

        self._next_request_id = 1
        self._responses_lock = Lock()
        self._responses: dict[int, TtsBackendResponse] = {}

        self._loop = asyncio.get_event_loop()

        thread = Thread(target=self._convert_thread, args=[0])
        thread.start()

    async def convert(self, request: TtsBackendRequest) -> TtsBackendResponse | None:
        logger.debug(f"Ask to convert {request.text}")

        internal_request = _Request(
            request_id=self._next_request_id,
            text=request.text,
            voice_id=self._get_voice_id(request.voice),
            voice_settings=VoiceSettings(
                stability=request.voice.elevenlabs.stability,
                similarity_boost=request.voice.elevenlabs.similarity_boost,
                style=request.voice.elevenlabs.style,
                use_speaker_boost=request.voice.elevenlabs.use_speaker_boost
            ),
            file_path=request.file_path
        )
        self._next_request_id = self._next_request_id + 1

        self._requests_lock.acquire_lock()
        self._requests.append(internal_request)
        self._requests_lock.release_lock()

        t0 = time.time()
        while True:
            dt = time.time() - t0
            if (dt > self._max_wait_time_sec):
                logger.error(
                    f"Ignoring result because waiting for too long id={internal_request.request_id} text={request.text}")
                break

            response = None
            self._responses_lock.acquire_lock()
            if internal_request.request_id in self._responses:
                response = self._responses.pop(internal_request.request_id)

            self._responses_lock.release_lock()

            if response is not None:
                return response

            await asyncio.sleep(1.0 / 20.0)

        return None

    def _convert_thread(self, thread_index: int):
        Logger.set_ctx("elevenlabs_thread")

        logger = Logger(__name__ + f".thread.{thread_index}")
        logger.debug("Thread started")

        while self._loop.is_running():
            request = None

            self._requests_lock.acquire_lock()
            if len(self._requests) > 0:
                request = self._requests.pop(0)
            self._requests_lock.release_lock()

            if request is not None:
                try:
                    response = self._handle_request_in_thread(request)

                    self._responses_lock.acquire_lock()
                    self._responses[request.request_id] = response
                    self._responses_lock.release_lock()
                except Exception as error:
                    logger.error(f"Conversion failed: {error}")
                    logger.debug(f"Request: {request}")

            time.sleep(1.0 / 10.0)

        logger.debug("Thread stopped")

    def _handle_request_in_thread(self, request: _Request) -> TtsBackendResponse:
        logger.debug(f"Handling request started {request.request_id}: '{request.text}'")
        audio = self._elevenlabs.text_to_speech.convert(
            voice_id=request.voice_id,
            output_format="mp3_44100_64",
            text=request.text,
            model_id=self._model_id,
            voice_settings=request.voice_settings,
            language_code=self._language_code
        )
        logger.debug(f"Handling request completed {request.request_id}: '{request.text}'")

        save(audio, request.file_path)

        return TtsBackendResponse(file_path=request.file_path)

    def _get_voice_id(self, voice: Voice) -> str:
        cfg = self._config.voices

        if voice.speaker_ref_id == 'chargen class00000000' and cfg.socucius:
            return cfg.socucius
        if voice.speaker_ref_id == 'vivec_god00000000':
            return cfg.d_male

        if voice.race_id == 'Argonian':
            return cfg.a_female if voice.female else cfg.a_male
        if voice.race_id == 'Breton':
            return cfg.b_female if voice.female else cfg.b_male
        if voice.race_id == 'Dark Elf':
            return cfg.d_female if voice.female else cfg.d_male
        if voice.race_id == 'High Elf':
            return cfg.h_female if voice.female else cfg.h_male
        if voice.race_id == 'Imperial':
            return cfg.i_female if voice.female else cfg.i_male
        if voice.race_id == 'Khajiit':
            return cfg.k_female if voice.female else cfg.k_male
        if voice.race_id == 'Nord':
            return cfg.n_female if voice.female else cfg.n_male
        if voice.race_id == 'Orc':
            return cfg.o_female if voice.female else cfg.o_male
        if voice.race_id == 'Redguard':
            return cfg.r_female if voice.female else cfg.r_male
        if voice.race_id == 'Wood Elf':
            return cfg.w_female if voice.female else cfg.w_male

        raise Exception(f"Cannot determine voice_id for this voice race_id={voice.race_id} female={voice.female}")
