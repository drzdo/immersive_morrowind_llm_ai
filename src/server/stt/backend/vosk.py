import asyncio
from util.logger import Logger
import queue
from pydantic import BaseModel
import sounddevice as sd  # type: ignore
from threading import Lock, Thread
import time
import json

from vosk import Model, KaldiRecognizer  # type: ignore

from stt.backend.abstract import AbstractSttBackend

logger = Logger(__name__)


class VoskSttBackend(AbstractSttBackend):
    class Config(BaseModel):
        device_index: int
        model_path: str

    def __init__(self, config: Config):
        super().__init__()

        logger.debug("Display input/output devices")
        logger.debug(sd.query_devices()) # type: ignore

        device_info = sd.query_devices(sd.default.device[config.device_index], 'input')  # type: ignore
        samplerate = int(device_info['default_samplerate']) # type: ignore

        logger.info("Device to use {} {}".format(sd.default.device[0], device_info)) # type: ignore

        logger.info("Build the model and recognizer objects. This may take a few minutes.")

        t0 = time.time()

        self._model = Model(config.model_path)
        self._recognizer = KaldiRecognizer(self._model, samplerate)
        self._recognizer.SetWords(False) # type: ignore

        logger.info(f"Vosk is ready after {time.time() - t0} sec")

        self._is_listening = False

        self._recognizing_text: str = ""
        self._recognized_text: str = ""
        self._texts_lock = Lock()
        self._main_event_loop = asyncio.get_event_loop()

        asyncio.get_event_loop().create_task(self._timer())

        thread = Thread(target=self._listening_thread)
        thread.start()

    async def _timer(self):
        Logger.set_ctx(f"VoskSttBackend")

        while self._main_event_loop.is_running():
            recognizing = None

            self._texts_lock.acquire_lock()
            if len(self._recognizing_text) > 0:
                recognizing = self._recognizing_text
                self._recognizing_text = ""
            self._texts_lock.release_lock()

            if recognizing is not None:
                self.on_recognizing(recognizing)

            # ---

            recognized = None

            self._texts_lock.acquire_lock()
            if len(self._recognized_text) > 0:
                recognized = self._recognized_text
                self._recognized_text = ""
            self._texts_lock.release_lock()

            if recognized is not None:
                self.on_recognized(recognized)

            await asyncio.sleep(1.0 / 10.0)

    def _should_stop_thread(self):
        asyncio.get_event_loop().is_running

    def _listening_thread(self):
        Logger.set_ctx("vosk_thread")

        logger = Logger(__name__ + ".thread")
        logger.debug("Thread started")

        try:
            accumulated_text: str = ""
            data_len = -1
            empty_data = None

            q = queue.Queue[bytes]()

            def recordCallback(indata, frames, time, status): # type: ignore
                if status: # type: ignore
                    logger.info(status) # type: ignore
                q.put(bytes(indata)) # type: ignore

            with sd.RawInputStream(dtype='int16', channels=1, callback=recordCallback): # type: ignore
                recognizer_has_result: bool = False

                while not self._main_event_loop.is_closed():
                    data: bytes = q.get() # type: ignore

                    if data_len != len(data):
                        data_len = len(data)
                        empty_data = bytes(bytearray(data_len))

                    if self._is_listening:
                        recognizer_has_result = self._recognizer.AcceptWaveform(data)  # type: ignore
                    else:
                        recognizer_has_result = self._recognizer.AcceptWaveform(empty_data)  # type: ignore

                    updated_accumulated_text = False
                    if recognizer_has_result:
                        result: str = self._recognizer.Result()  # type: ignore
                        result_dict = json.loads(result)  # type: ignore
                        text = result_dict.get('text', '').strip()

                        if len(text) > 0:
                            accumulated_text = (accumulated_text + " " + text).strip()
                            updated_accumulated_text = True

                    if self._is_listening and updated_accumulated_text:
                        logger.debug(f"Recognizing '{accumulated_text}'")

                        self._texts_lock.acquire_lock()
                        self._recognizing_text = accumulated_text
                        self._texts_lock.release_lock()

                    if not self._is_listening and len(accumulated_text) > 0:
                        logger.debug(f"Flushing '{accumulated_text}'")

                        self._texts_lock.acquire_lock()
                        self._recognized_text = (self._recognized_text + " " + accumulated_text).strip()
                        self._texts_lock.release_lock()

                        accumulated_text = ""

        except Exception as e:
            logger.error(f"Vosk error: {str(e)}")

        logger.debug("Thread ended")

    def start_listening(self):
        self._is_listening = True
        logger.debug(f"Start listening")

    def stop_listening(self):
        self._is_listening = False
        logger.debug(f"Stop listening")
