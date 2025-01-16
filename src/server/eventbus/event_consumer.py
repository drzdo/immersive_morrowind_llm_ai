from abc import ABC, abstractmethod
from util.logger import Logger
from typing import Any, Callable, Coroutine

from eventbus.event import Event

logger = Logger(__name__)


class EventConsumer(ABC):
    @abstractmethod
    def register_handler(self, handler: Callable[[Event], Coroutine[Any, Any, None]]):
        pass
