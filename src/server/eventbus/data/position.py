import math
from typing import Self
from pydantic import BaseModel


class Position(BaseModel):
    x: float
    y: float
    z: float

    def distance(self, other: Self):
        dx = other.x - self.x
        dy = other.y - self.y
        dz = other.z - self.z

        return math.sqrt(dx*dx + dy*dy + dz*dz)
