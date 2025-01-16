from pydantic import BaseModel


class NpcResponseReactionData(BaseModel):
    reaction: str
    disposition_change: int
    attack: bool
    follow: bool
    help: bool
    stop_follow: bool
    give_gold_to_target: int
    take_gold_from_target: int
