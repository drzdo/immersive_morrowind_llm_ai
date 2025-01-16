import os
from threading import Lock

from pydantic import BaseModel

class FileListRotation:
    class Config(BaseModel):
        max_files_count: int
        file_name_format: str

    def __init__(self, config: Config, directory: str) -> None:
        self._config = config
        self._directory = directory

        self.next_index = 0

        self.lock = Lock()

        os.makedirs(directory, exist_ok=True)

    def get_next_filepath(self) -> str:
        self.lock.acquire_lock()

        filename = self._config.file_name_format.format(self.next_index)
        filepath = os.path.join(self._directory, filename)
        self.next_index = (self.next_index + 1) % self._config.max_files_count

        self.lock.release_lock()

        return filepath


