import json
from typing import Any

def read_json_cp1251(path: str) -> Any:
    with open(path, 'r', encoding='cp1251') as f:
        data = json.load(f)
    return data

def write_json_cp1251(path: str, data: Any):
    with open(path, 'w', encoding='cp1251') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data
