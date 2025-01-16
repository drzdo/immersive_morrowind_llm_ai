from util.logger import Logger

import azure.cognitiveservices.speech as speechsdk # type: ignore
from pydantic import BaseModel

from stt.backend.abstract import AbstractSttBackend

logger = Logger(__name__)


class MicrosoftSpeechSttBackend(AbstractSttBackend):
    class Config(BaseModel):
        key: str
        region: str
        language: str
        known_words: str

    def __init__(self, config: Config):
        super().__init__()

        self._speech_config = speechsdk.SpeechConfig(
            subscription=config.key,
            region=config.region
        )
        self._speech_config.set_profanity(speechsdk.ProfanityOption.Raw)

        self._speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self._speech_config,
            language=config.language
        )

        self._grammar = speechsdk.PhraseListGrammar.from_recognizer(self._speech_recognizer)

        phrases_str = config.known_words
        phrases = phrases_str.split(',')
        for s in phrases:
            self._grammar.addPhrase(s)

        self._speech_recognizer.recognizing.connect(self._handle_recognizing) # type: ignore
        self._speech_recognizer.recognized.connect(self._handle_recognized) # type: ignore

        self._messages_accumulated: list[str] = []
        self._current_message: str = ""

        self._is_listening = False
        self._started_recognizing = False

    def start_listening(self):
        self._messages_accumulated = []
        self._current_message = ""

        self._is_listening = True

        logger.debug(f"Start listening")
        self._speech_recognizer.start_continuous_recognition_async()

    def stop_listening(self):
        self._is_listening = False
        self._speech_recognizer.stop_continuous_recognition_async()
        logger.debug(f"Stop listening")

        if not self._started_recognizing:
            self._flush()

    def _flush(self):
        m = self._get_accumulated_message()

        self._current_message = ""
        self._messages_accumulated.clear()

        logger.debug(f"Flushing: '{m}'")
        if len(m) > 0:
            self.on_recognized(m)

    def _get_accumulated_message(self):
        message = " ".join(self._messages_accumulated) + " " + self._current_message
        message = message.strip()
        return message

    def _handle_recognizing(self, e): # type: ignore
        logger.debug(f"Recognizing: '{e.result.text}'") # type: ignore

        self._started_recognizing = True
        self._current_message = e.result.text # type: ignore

        m = self._get_accumulated_message()
        if len(m) > 0:
            self.on_recognizing(m)

    def _handle_recognized(self, e): # type: ignore
        m = str(e.result.text) # type: ignore
        logger.debug(f"Recognized: '{m}'")

        self._started_recognizing = False

        self._messages_accumulated.append(m)
        self._current_message = ""

        if self._is_listening:
            logger.debug("Accumulated by still continue listening...")
        else:
            self._flush()
