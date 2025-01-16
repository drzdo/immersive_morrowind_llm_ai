from util.now_ms import now_ms

_last_ms: int = 0
_inc: int = 0

def gen_id(suffix: str | None = None) -> str:
    global _last_ms
    global _inc

    ms = now_ms()
    if ms == _last_ms:
        _inc = _inc + 1
    else:
        _last_ms = ms
        _inc = 0

    if suffix:
        return f"{ms}.{_inc}_{suffix}"
    else:
        return f"{ms}.{_inc}"
