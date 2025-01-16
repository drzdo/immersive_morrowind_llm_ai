from util.logger import Logger
import os
from pydantic import BaseModel
import yaml
from pathvalidate import sanitize_filename

logger = Logger(__name__)

class Database:
    class Config(BaseModel):
        directory: str

    def __init__(self, config: Config, player_name: str) -> None:
        self._config = config

        self._root_dir = os.path.join(self._config.directory, sanitize_filename(player_name))
        logger.info(f"Database will be located at {self._root_dir}")

        os.makedirs(self._root_dir, exist_ok=True)

    def save_model(self, *, path: list[str], value: BaseModel) -> None:
        d = value.model_dump(mode='json')
        text = yaml.dump(d, allow_unicode=True)

        filepath = self._get_filepath_model(path)
        self._save(filepath, text)

    def save_text(self, *, path: list[str], text: str) -> None:
        filepath = self._get_filepath_text(path)
        self._save(filepath, text)

    def load_model[T: BaseModel](self, *, type: type[T], path: list[str] = []) -> T | None:
        filepath = self._get_filepath_model(path)
        if not os.path.exists(filepath):
            logger.debug(f"File is absent for model at {filepath}")
            return None

        text = self._load(filepath)
        d = yaml.safe_load(text)
        return type.model_validate(d)

    def load_text(self, *, path: list[str] = []) -> str | None:
        filepath = self._get_filepath_text(path)
        if not os.path.exists(filepath):
            logger.debug(f"File is absent for text at {filepath}")
            return None

        return self._load(filepath)

    def _get_filepath(self, path: list[str], file_ext: str):
        if len(path) == 0:
            raise Exception(f"Path must contain at least file name")

        path_without_file = path[:-1]

        full_dir = os.path.join(self._root_dir, *path_without_file)
        os.makedirs(full_dir, exist_ok=True)

        full_path = os.path.join(full_dir, f"{sanitize_filename(path[-1])}.{file_ext}")
        return full_path

    def _get_filepath_model(self, path: list[str]):
        return self._get_filepath(path, 'yml')

    def _get_filepath_text(self, path: list[str]):
        return self._get_filepath(path, 'txt')

    def _save(self, filepath: str, text: str) -> None:
        f = open(filepath, 'w', encoding='utf-8')
        f.write(text)
        f.close()

    def _load(self, filepath: str) -> str:
        f = open(filepath, 'r', encoding='utf-8')
        c = f.read()
        f.close()
        return c
