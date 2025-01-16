from typing import Optional

from pydantic import BaseModel


class TopicDialogue(BaseModel):
    source_mod: str
    type: str


class TopicInfo(BaseModel):
    source_mod: str
    text: str
    type: str
    cell: Optional[str] = None
    disposition: Optional[int] = None


class Topic(BaseModel):
    topic_text: str
    topic_response: str
    dialogue: TopicDialogue
    info: TopicInfo


class DialogData(BaseModel):
    greet_text: str
    npc_ref_id: str
    topics: list[Topic]
