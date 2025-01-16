from stt.backend.abstract import AbstractSttBackend


class DummySttBackend(AbstractSttBackend):
    def start_listening(self):
        pass

    def stop_listening(self):
        pass
