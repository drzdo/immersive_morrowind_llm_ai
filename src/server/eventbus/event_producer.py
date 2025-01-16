from abc import ABC, abstractmethod

from eventbus.event import Event


class EventProducer(ABC):
    @abstractmethod
    def produce_event(self, event: Event):
        pass
