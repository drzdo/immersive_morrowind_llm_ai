from typing import Literal, TypeAlias, Union

# "attack", "killing", "stealing", "pickpocket", "theft", "trespass", and "werewolf"
CrimeType: TypeAlias = Union[
    Literal['attack'],
    Literal['killing'],
    Literal['stealing'],
    Literal['pickpocket'],
    Literal['theft'],
    Literal['trespass'],
    Literal['werewolf'],
]
