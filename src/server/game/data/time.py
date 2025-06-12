from typing import Self
from pydantic import BaseModel, Field

from util.now_ms import now_ms


class GameTime(BaseModel):
    day: int
    month: int
    year: int
    hour: float

    def to_unix_timestamp_sec(self):
        t = 0

        sec_per_h = 3600
        t += self.hour * sec_per_h
        t += self.day * sec_per_h * 24
        t += self.month * sec_per_h * 24 * 30
        t += self.year * sec_per_h * 24 * 30 * 12

        return t

    def __lt__(self, other: Self):
        return self.to_unix_timestamp_sec() < other.to_unix_timestamp_sec()

    def __gt__(self, other: Self):
        return self.to_unix_timestamp_sec() > other.to_unix_timestamp_sec()

    def __le__(self, other: Self):
        return self.to_unix_timestamp_sec() <= other.to_unix_timestamp_sec()

    def __ge__(self, other: Self):
        return self.to_unix_timestamp_sec() >= other.to_unix_timestamp_sec()

class Time(BaseModel):
    real_time_ms: int = Field(default_factory=now_ms)
    game_time: GameTime

    def __lt__(self, other: Self):
        if self.game_time == other.game_time:
            return self.real_time_ms < other.real_time_ms
        else:
            return self.game_time.to_unix_timestamp_sec() < other.game_time.to_unix_timestamp_sec()

    def __gt__(self, other: Self):
        if self.game_time == other.game_time:
            return self.real_time_ms > other.real_time_ms
        else:
            return self.game_time.to_unix_timestamp_sec() > other.game_time.to_unix_timestamp_sec()

    def __le__(self, other: Self):
        if self.game_time == other.game_time:
            return self.real_time_ms <= other.real_time_ms
        else:
            return self.game_time.to_unix_timestamp_sec() <= other.game_time.to_unix_timestamp_sec()

    def __ge__(self, other: Self):
        if self.game_time == other.game_time:
            return self.real_time_ms >= other.real_time_ms
        else:
            return self.game_time.to_unix_timestamp_sec() >= other.game_time.to_unix_timestamp_sec()
