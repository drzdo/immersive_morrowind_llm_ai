from abc import ABC, abstractmethod
from typing import Callable
from eventbus.event import Event


class AbstractEventBusBackend(ABC):
    @abstractmethod
    def start(self, callback: Callable[[Event], None]):
        pass

    @abstractmethod
    def publish_event_to_game(self, event: Event):
        pass

    @abstractmethod
    def is_connected_to_game(self) -> bool:
        pass
