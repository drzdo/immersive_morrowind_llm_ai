import asyncio
from typing import Literal, Union
from game.data.npc import Npc
from game.service.util.llm_json_fixer import LlmJsonFixer
from util.logger import Logger
from pydantic import BaseModel, Field

from llm.system import LlmSystem


logger = Logger(__name__)


class RequestInDialog(BaseModel):
    player_text: str
    known_topics: list[str]
    target: Npc


class RequestNotInDialog(BaseModel):
    player_text: str
    npcs: list[Npc]

# ---


class ResponseDataCommon:
    class StopFollow(BaseModel):
        type: Literal['stop_follow']

    class GameMasterUpdateNpcMemory(BaseModel):
        type: Literal['gamemaster_update_npc_memory']
        npc_ref_ids: list[str]

    class GameMasterStopCombat(BaseModel):
        type: Literal['gamemaster_stop_combat']

    union = Union[
        StopFollow,
        GameMasterUpdateNpcMemory,
        GameMasterStopCombat,
    ]


_JSON_FORMAT_COMMON = """
type Response = {
    // Игрок как game master хочет изменить память одного или нескольких NPC.
    type: "gamemaster_update_npc_memory"

    // Список ref_id тех NPC, память которых хочет изменить игрок.
    npc_ref_ids: string[]
}"""

# ---


class ResponseInDialog(BaseModel):
    class TriggerTopic(BaseModel):
        type: Literal['trigger_dialog_topic']
        topic: str

    class ListTopics(BaseModel):
        type: Literal['list_dialog_topics']

    data: Union[
        ResponseDataCommon.union,
        ResponseDataInDialog.TriggerTopic,
        ResponseDataInDialog.ListTopics,
    ] = Field(discriminator='type')


_JSON_FORMAT_IN_DIALOG = """ | {
    // Игрок конкретно просит NPC поговорить на одну из конкретных тем, которые известны NPC.
    type: "trigger_dialog_topic"

    // Как дословно называется эта тема.
    topic: string
} | {
    // Игрок просит NPC рассказать, на какие темы с этим NPC можно поговорить.
    type: "list_dialog_topics"
}
"""

# ---


class ResponseNotInDialog(BaseModel):
    data: Union[
        ResponseDataCommon.union,
        ResponseDataCommon.union,
    ] = Field(discriminator='type')


_JSON_FORMAT_NOT_IN_DIALOG = """"""


class PlayerIntentionAnalyzer:
    def __init__(self, llm: LlmSystem) -> None:
        self._llm_session = llm.create_session()
        self._lock = asyncio.Lock()
        self._json_fixer = LlmJsonFixer(self._llm_session)

    async def analyze_player_intention_in_dialog(self, request: RequestInDialog) -> ResponseInDialog:
        await self._lock.acquire()
        try:
            instructions = """Ты наблюдаешь за диалогом игрока и NPC в мире Elder Scrolls Morrowind.
Игрок может сказать что-то от имени своего персонажа, а может сказать что-то от имени режисёра (он же game master, dungeon master).
Твоя задача - понять, что хочет игрок и напечатать вывод в формате JSON:

""" + _JSON_FORMAT_COMMON + _JSON_FORMAT_IN_DIALOG + """

Например, твой вывод может быть

```json
{
    type: "trigger_dialog_topic"
    topic: "Биография"
}
```

или другой пример:

```json
{
    type: "gamemaster_update_npc_memory"
    npc_ref_ids: ["caius cosades00000000"]
}
```
"""

            self._llm_session.reset(
                system_instructions=instructions,
                messages=[]
            )

            llm_response = await self._llm_session.send_message(user_text=f"(игрок говорит) {request.player_text}")
            return await self._json_fixer.fix_json(ResponseInDialog, _JSON_FORMAT_COMMON + _JSON_FORMAT_IN_DIALOG, llm_response)
        finally:
            self._lock.release()

    async def analyze_player_intention_not_in_dialog(self, request: RequestNotInDialog) -> ResponseNotInDialog:
        await self._lock.acquire()
        try:
            instructions = """Ты наблюдаешь за разговоров игрока и NPC-ей в мире Elder Scrolls Morrowind.
Игрок может сказать что-то от имени своего персонажа, а может сказать что-то от имени режисёра (он же game master, dungeon master).
Твоя задача - понять, что хочет игрок и напечатать вывод в формате JSON:

""" + _JSON_FORMAT_COMMON + _JSON_FORMAT_NOT_IN_DIALOG + """

Например, твой вывод может быть

```json
{
    type: "gamemaster_stop_combat"
}
```

или другой пример:

```json
{
    type: "gamemaster_update_npc_memory"
    npc_ref_ids: ["caius cosades00000000"]
}
```
"""

            self._llm_session.reset(
                system_instructions=instructions,
                messages=[]
            )

            llm_response = await self._llm_session.send_message(user_text=f"(игрок говорит) {request.player_text}")
            return await self._json_fixer.fix_json(ResponseNotInDialog, _JSON_FORMAT_COMMON + _JSON_FORMAT_NOT_IN_DIALOG, llm_response)
        finally:
            self._lock.release()
