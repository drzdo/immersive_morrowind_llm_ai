from pydantic import BaseModel


class TopicData(BaseModel):
    topic_text: str
    topic_response: str
