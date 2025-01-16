import json
from typing import Any

def read_json_cp1251(path: str) -> Any:
    f = open(path, 'r', encoding='cp1251')
    data = json.load(f)
    f.close()
    return data

def write_json_cp1251(path: str, data: Any):
    f = open(path, 'w', encoding='cp1251')
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.close()
    return data
