import asyncio
from typing import Literal, Union
from pydantic import BaseModel, Field
from stt.backend.whisper import WhisperSttBackend
from util.logger import Logger

from eventbus.event import Event
from eventbus.event_data.event_data_from_server import EventDataFromServer
from eventbus.event_producer import EventProducer
from stt.backend.abstract import AbstractSttBackend
from stt.backend.msspeech import MicrosoftSpeechSttBackend
from stt.backend.dummy import DummySttBackend
from stt.backend.vosk import VoskSttBackend
from stt.input import VoiceRecognitionInput
from util.colored_lines import green

logger = Logger(__name__)


class SttSystem:
    class Config(BaseModel):
        class Dummy(BaseModel):
            type: Literal['dummy']

        class Vosk(BaseModel):
            type: Literal['vosk']
            vosk: VoskSttBackend.Config

        class MicrosoftSpeech(BaseModel):
            type: Literal['microsoft_speech']
            microsoft_speech: MicrosoftSpeechSttBackend.Config

        class Whisper(BaseModel):
            type: Literal['whisper']
            whisper: WhisperSttBackend.Config

        system: Union[Dummy, Vosk, MicrosoftSpeech, Whisper] = Field(discriminator='type')
        delayed_stop_sec: float

    def __init__(self, config: Config, producer: EventProducer):
        self._config = config
        self._producer = producer

        self._generation_index = 0
        self._is_listening = False
        self._is_cancelled = False
        self._stop_listening_at_time = None

        self._backend = self._create_backend()
        self._backend.on_recognizing = self._handle_recognizing
        self._backend.on_recognized = self._handle_recognized

        self._input = VoiceRecognitionInput()
        self._input.on_start_listening = self._handle_start_listening
        self._input.on_stop_listening = self._handle_stop_listening
        self._input.on_cancel_listening = self._handle_cancel_listening

        self._main_event_loop = asyncio.get_event_loop()

    def _handle_start_listening(self):
        if self._is_listening:
            return

        self._stop_listening_at_time = None
        self._is_cancelled = False
        self._is_listening = True
        self._generation_index = self._generation_index + 1

        self._backend.start_listening()
        self._producer.produce_event(
            Event(data=EventDataFromServer.SttStartListening(type='stt_start_listening')))

    def _handle_stop_listening(self):
        if not self._is_listening:
            return

        current_generation = self._generation_index
        if self._config.delayed_stop_sec > 0:
            self._main_event_loop.call_later(
                self._config.delayed_stop_sec,
                lambda: self._stop_listening_if_in_same_generation(current_generation)
            )
        else:
            self._do_stop_listening()

    def _stop_listening_if_in_same_generation(self, expected_generation_index: int):
        if expected_generation_index == self._generation_index:
            self._do_stop_listening()

    def _do_stop_listening(self):
        self._is_listening = False
        self.stop_listening_at_time = None

        self._backend.stop_listening()
        self._producer.produce_event(Event(data=EventDataFromServer.SttStopListening(type='stt_stop_listening')))

    def _handle_cancel_listening(self):
        if not self._is_listening:
            return

        self._is_cancelled = True
        self._is_listening = False
        self.stop_listening_at_time = None

        self._backend.stop_listening()
        self._producer.produce_event(Event(data=EventDataFromServer.SttStopListening(type='stt_stop_listening')))

    def _create_backend(self) -> AbstractSttBackend:
        system = self._config.system

        backend: AbstractSttBackend
        match system.type:
            case 'dummy':
                logger.info(f"Speech-to-text system is set to {green('dummy')}")
                backend = DummySttBackend()
            case 'microsoft_speech':
                logger.info(f"Speech-to-text system is set to {green('Microsoft Speech')}")
                backend = MicrosoftSpeechSttBackend(system.microsoft_speech)
            case 'vosk':
                logger.info(f"Speech-to-text system is set to {green('Vosk')}")
                backend = VoskSttBackend(system.vosk)
            case 'whisper':
                logger.info(f"Speech-to-text system is set to {green('Whisper')}")
                backend = WhisperSttBackend(system.whisper)

        return backend

    def _handle_recognizing(self, text: str):
        if self._is_cancelled:
            logger.debug(f"Cancel recognizing result because cancelled: {text}")
            return

        text = self._postprocess_text(text)

        self._producer.produce_event(Event(data=EventDataFromServer.SttRecognitionUpdate(
            text=text,
            type='stt_recognition_update'
        )))

    def _handle_recognized(self, text: str):
        if self._is_cancelled:
            logger.debug(f"Cancel recognizing result because cancelled: {text}")
            return

        text = self._postprocess_text(text)

        logger.info(f"Recognized: '{text}'")

        self._producer.produce_event(Event(data=EventDataFromServer.SttRecognitionComplete(
            text=text,
            type='stt_recognition_complete'
        )))

    def _postprocess_text(self, text: str):
        return text.replace("ё", "е").replace("Ё", "Е").strip()
