from game.i18n.i18n import I18n
from util.logger import Logger
import os


logger = Logger(__name__)


class CellNameProvider:
    def __init__(self, morrowind_data_files_dir: str, i18n: I18n) -> None:
        self._cell_name_to_name: dict[str, str] = {}
        self._i18n = i18n

        morrowind_data_dir = morrowind_data_files_dir
        files = ["morrowind.cel", "tribunal.cel", "bloodmoon.cel"]
        for filename in files:
            filepath = os.path.join(morrowind_data_dir, filename)
            if os.path.exists(filepath):
                file = open(filepath, "r", encoding="cp1251")
                lines = file.readlines()
                file.close()

                for line in lines:
                    components = line.strip().split("\t")
                    if len(components) == 2:
                        k = components[0].strip()
                        v = components[1].strip()
                        if len(k) > 0 and len(v) > 0:
                            self._cell_name_to_name[k] = v

        logger.info(f"Registered {len(self._cell_name_to_name)} cell name mappings")

    def get_cell_name(self, cell_name: str):
        if cell_name in self._cell_name_to_name:
            return self._cell_name_to_name[cell_name]
        elif len(cell_name) > 0:
            return cell_name
        else:
            return self._i18n.str("где-то за городом")
