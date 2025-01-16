from typing import Literal, Union

from pydantic import BaseModel


class LlmMessage(BaseModel):
    role: Union[Literal['user'], Literal['model']]
    text: str
