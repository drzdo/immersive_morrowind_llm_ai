from typing import Optional
from pydantic import BaseModel


class Cell(BaseModel):
    class Region(BaseModel):
        id: str
        name: str

    id: str
    name: Optional[str] = None
    display_name: str
    is_exterior: bool
    is_interior: bool
    rest_is_illegal: bool
    region: Optional[Region] = None
