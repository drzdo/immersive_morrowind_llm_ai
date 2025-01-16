import time

def now_ms() -> int:
    return round(time.time() * 1000)
