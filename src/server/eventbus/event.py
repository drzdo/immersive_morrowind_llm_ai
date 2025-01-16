from typing import Optional, Union
from pydantic import BaseModel, Field

from eventbus.event_data.event_data_from_game import EventDataFromGameUnion
from eventbus.event_data.event_data_from_server import EventDataFromServerUnion
from eventbus.event_data.event_data_rpc import EventDataRpcUnion


class Event(BaseModel):
    event_id: int = Field(init=False, default=-1)
    response_to_event_id: Optional[int] = Field(init=False, default=None)

    data: Union[
        EventDataFromGameUnion,
        EventDataFromServerUnion,
        EventDataRpcUnion
    ] = Field(discriminator='type')
