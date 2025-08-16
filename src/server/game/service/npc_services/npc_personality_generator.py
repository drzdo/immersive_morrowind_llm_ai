import asyncio
import random
from typing import NamedTuple
from eventbus.data.npc_data import NpcData
from game.data.npc import NpcMemory
from game.service.util.llm_json_fixer import LlmJsonFixer
from llm.session import LlmSession
from tts.voice import Voice

_JSON_FORMAT = """
```
// Интерфейс в котором должен быть сделан вывод.
interface Output {
    // Что персонаж помнит, и какое у персонажа к этому отношение.
    memory_entries: MemoryEntry[]

    // При каких условиях будет меняться отношение персонажа к чему-то и как будет меняться.
    // Условие должно строится примерно по такому правилу: "если со мной случится X, то я сделаю Y"
    // Действие "Y" может добавлять новые memory_entries или менять интепретацию существующих.
    // По сути, эти правила - это способ задать траекторию развития характера персонажа.
    update_rules: string[]
}

interface MemoryEntry {
    // Факты - что именно произошло с персонажем. Сухие факты без интерпретации.
    fact: string

    // Как персонаж интерпретировал эти факты, как повлияло на отношение к кому-либо или чему-либо.
    interpretation: string
}
```
"""

class NpcPersonalityGenerator():
    class GeneratedNpc(NamedTuple):
        memory: NpcMemory
        voice: Voice

    def __init__(self, llm_session: LlmSession) -> None:
        self._llm_session = llm_session
        self._json_fixer = LlmJsonFixer(llm_session)
        self._lock = asyncio.Lock()

    async def generate(self, npc_data: NpcData, generation_suggestion: str | None = None) -> GeneratedNpc:
        voice = Voice(
            speaker_ref_id=npc_data.ref_id,
            race_id=npc_data.race and npc_data.race.id,
            female=npc_data.female,
            pitch=random.uniform(0.9, 1.1),
            elevenlabs=Voice.Elevenlabs(
                stability=random.uniform(0.3, 1.0),
                style=random.uniform(0.3, 0.7),
                similarity_boost=random.uniform(0.3, 0.7),
            ),
            accent='none'  # TODO: probability based per class
        )

        await self._lock.acquire()
        try:
            self._llm_session.reset(
                system_instructions="""
Твоя задача - сгенерировать бекграунд персонажа из мира Elder Scrolls Morrowind.
Результат должен быть в виде JSON. Тип JSON должен соответствовать `Output` TypeScript интерфейсу ниже:

""" + _JSON_FORMAT + """

Вот пример вывода если персонажа "Губерон, мужчина, данмер, состоит во фракции Гильдия магов".
- Вывод должен быть от имени персонажа (не "Губерон любит что-то", а "я люблю что-то")
- придумай до 30 memory_entries и около 10 update_rules. Пусть они будут связаны общей логикой, и персонаж получится цельный.
  Добавь факты о том, где персонаж родился, вырос, бывал, работал, общался, взаимодействовал, дружил, враждовал.

```json
{
    "memory_entries": [
        {
            "fact": "Я вступил в гильдию магов семь лет назад и долго там служил",
            "interpretation": "Я устал от гильдии магов и терпеть её не могу, но там хорошо платят - поэтому я там всё ещё остаюсь."
        },
        {
            "fact": "Со мной говорил эльф Никанор и Вивеке и культе Нереварина",
            "interpretation": "Разговор с Никанором был крайне скучным и неинтересным. Если он следующий раз ко мне подойдёт, то я просто пошлю его.'
        }
    ],
    "update_rules": [
        "если со мной кто-то будет говорить с искренним вниманием ко мне и заботой, то я отвечу взаимностью и предложу выпить суджаммы",
        "если кто-то скажет, что Вивек негодяй - то я запомню это и запишу этого человека в список тех, с кем нельзя говорить",
        "если я услышу, как кто-то ругается матом, то я осужу его публично и громко"
    ]
}
```
""",
                messages=[]
            )
            text = await self._llm_session.send_message(
                user_text=f"""Персонажа зовут {npc_data.name}, это - {"женщина" if npc_data.female else "мужчина"} расы {npc_data.race.name if npc_data.race else ""}.
Класс - {npc_data.class_name}, уровень {npc_data.stats.other.level if npc_data.stats else "1"}.

{generation_suggestion}"""
            )

            memory = await self._json_fixer.fix_json(NpcMemory, _JSON_FORMAT, text)
            return NpcPersonalityGenerator.GeneratedNpc(memory, voice)
        finally:
            self._lock.release()
