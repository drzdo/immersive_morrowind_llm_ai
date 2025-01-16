from abc import ABC, abstractmethod
from typing import Callable


class AbstractSttBackend(ABC):
    def __init__(self):
        self.on_recognizing: Callable[[str], None]
        self.on_recognized: Callable[[str], None]

    @abstractmethod
    def start_listening(self):
        pass

    @abstractmethod
    def stop_listening(self):
        pass
