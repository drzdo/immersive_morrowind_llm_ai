import asyncio
import time
import numpy as np
from threading import Lock, Thread

from pydantic import BaseModel

from util.logger import Logger

from .abstract import AbstractSttBackend
import sounddevice as sd  # type: ignore
import whisper # type: ignore

logger = Logger(__name__)

class WhisperSttBackend(AbstractSttBackend):
    class Config(BaseModel):
        device_index: int
        model_name: str
        device: str
        language: str
        initial_prompt: str

    def __init__(self, config: Config):
        super().__init__()
        self._config = config

        logger.debug("Display input/output audio devices")
        logger.debug(sd.query_devices()) # type: ignore

        # sd.default.latency = 'low' # type: ignore
        device_info = sd.query_devices(sd.default.device[config.device_index], 'input')  # type: ignore
        # samplerate = int(device_info['default_samplerate']) # type: ignore

        logger.info("Audio device to use {} {}".format(sd.default.device[0], device_info)) # type: ignore

        self._main_event_loop = asyncio.get_event_loop()
        self._is_listening = False

        logger.info("Loading whisper model...")
        self._model = whisper.load_model(self._config.model_name, self._config.device)
        logger.info(f"Loading whisper model complete: device={self._model.device} multilingual={self._model.is_multilingual}")

        self._lock = Lock()
        self._recognized_texts: list[str] = []

        asyncio.get_event_loop().create_task(self._main_thread_timer())

        self._thread = Thread(name="whisper_thread", target=self._listening_thread)
        self._thread.start()

    def start_listening(self):
        self._is_listening = True
        logger.debug(f"Start listening")

    def stop_listening(self):
        self._is_listening = False
        logger.debug(f"Stop listening")

    async def _main_thread_timer(self):
        while not self._main_event_loop.is_closed():
            final_str: str | None = None
            self._lock.acquire_lock()
            if len(self._recognized_texts) > 0:
                final_str = "\n".join(self._recognized_texts)
                self._recognized_texts.clear()
            self._lock.release_lock()

            if final_str:
                self.on_recognized(final_str)

            await asyncio.sleep(1.0 / 10.0)

    def _listening_thread(self):
        logger = Logger(__name__ + ".thread")
        logger.debug("Thread started")

        try:
            audio_buffer = []

            def recordCallback(indata, frames, time, status): # type: ignore
                if status: # type: ignore
                    logger.warning(f"Status in recordCallback is not null: {status}") # type: ignore

                if self._is_listening:
                    audio_buffer.append(indata.flatten()) # type: ignore

            # samplerate=16000,
            with sd.InputStream(dtype='float32', channels=1, samplerate=16000, callback=recordCallback): # type: ignore
                while not self._main_event_loop.is_closed():
                    if len(audio_buffer) > 0 and not self._is_listening: # type: ignore
                        data_for_model = np.concatenate(audio_buffer) #.astype(np.float32) / 32767 # type: ignore
                        model_result = self._model.transcribe(data_for_model, fp16=False, language=self._config.language, initial_prompt=self._config.initial_prompt) # type: ignore
                        logger.debug(f"Recognized '{model_result}'")

                        audio_buffer = []
                        text: str = model_result["text"].strip() # type: ignore

                        if text:
                            self._lock.acquire_lock()
                            self._recognized_texts.append(text) # type: ignore
                            self._lock.release_lock()

                    time.sleep(1.0 / 60.0)

        except Exception as e:
            logger.error(f"Whisper error: {str(e)}")

        logger.debug("Thread ended")

