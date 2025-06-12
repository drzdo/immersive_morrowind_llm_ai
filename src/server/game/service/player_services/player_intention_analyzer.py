import asyncio
from typing import Literal, Optional
from eventbus.data.actor_ref import ActorRef
from game.service.util.prompt_builder import PromptBuilder
from util.logger import Logger
from pydantic import BaseModel

from llm.system import LlmSystem


logger = Logger(__name__)


class PlayerIntentionAnalyzer:
    class Response(BaseModel):
        trigger_dialog_topic: str | None = None
        list_available_dialog_topics: bool = False
        npc_stop_follow: bool = False
        npc_shut_up: bool = False
        npc_stop_combat: bool = False
        sheogorath_level: Literal['normal', 'mad'] | None = None

    def __init__(self, llm: LlmSystem) -> None:
        self._llm_session = llm.create_session()
        self._lock = asyncio.Lock()

    async def analyze_player_intention(self, text: str, known_topics: list[str], target: Optional[ActorRef]) -> Response:
        if "лично" in text:  # i18n
            return PlayerIntentionAnalyzer.Response()

        await self._lock.acquire()
        try:
            instructions = self._build_instructions(text, known_topics, target)

            self._llm_session.reset(
                system_instructions=instructions,
                messages=[]
            )

            log_context = "\n".join(
                ["Player intention analyzer", f"Known topics: {known_topics}"]
            )
            llm_response = await self._llm_session.send_message(
                user_text=f"(игрок говорит) {text}",
                log_name="player_intent",
                log_context=log_context
            )

            response = PlayerIntentionAnalyzer.Response()

            lines = llm_response.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith('trigger_dialog_topic'):
                    triggered_topic = line.split(':')[1].strip()
                    response.trigger_dialog_topic = self._match_exact_topic_name(known_topics, triggered_topic)
                if line.startswith('list_available_dialog_topics'):
                    response.list_available_dialog_topics = True
                if line.startswith('npc_shut_up'):
                    response.npc_shut_up = True
                if line.startswith('npc_stop_combat'):
                    response.npc_stop_combat = True
                if line.startswith('npc_stop_follow'):
                    response.npc_stop_follow = True
                if line.startswith('npc_sheogorath_normal'):
                    response.sheogorath_level = 'normal'
                if line.startswith('npc_sheogorath_mad'):
                    response.sheogorath_level = 'mad'

            logger.debug(f"Player intention from {text} is {response}")

            return response
        finally:
            self._lock.release()

    def _build_instructions(self, text: str, known_topics: list[str], target: Optional[ActorRef]) -> str:
        b = PromptBuilder()

        b.line("Ты наблюдаешь за диалогом игрока и NPC в мире Elder Scrolls Morrowind. Твоя задача - понять, что хочет игрок.")

        if known_topics:
            b.paragraph()
            b.line(f"""
{b.get_option_index_and_inc()}. Если игрок говорит, что хочет обсудить какой-то вопрос 'предметно', то
- найди из списка тем ту, которая наиболее близко связана с вопросом игрока,
- и выведи 'trigger_dialog_topic:TOPIC', где вместо TOPIC подставь имя темы.
Вот список тем: {', '.join(known_topics)}.
Например, у тебя такой список тем: 'задания, вступить в Гильдию магов'.
Если игрок говорит 'я хочу предметно обсудить следующее распоряжение', то наиболее близкой темой будет 'задания', и поэтому ты выведешь 'trigger_dialog_topic:задания'.
Если же игрок говорит 'я хотел бы обсудить вступление в гильдию предметно', то наиболее близкой темой будет 'вступить в Гильдию магов', и поэтому ты выведешь 'trigger_dialog_topic:вступить в Гильдию магов'
""")

        b.paragraph()
        b.line(f"""
{b.get_option_index_and_inc()}. Если игрок спрашивает, на какие темы вы можете поговорить 'предметно' - то выведи 'list_available_dialog_topics'.
""")

        b.paragraph()
        b.line(f"""
{b.get_option_index_and_inc()}. Если игрок хочет, чтобы NPC замолчали, то выведи 'npc_shut_up'.
{b.get_option_index_and_inc()}. Если игрок хочет, чтобы NPC прекратили драку, то выведи 'npc_stop_combat'.
{b.get_option_index_and_inc()}. Если игрок хочет, чтобы NPC прекратили следовать за ним, то выведи 'npc_stop_follow'.
""")

        if target is None:
            b.line(f"""
    {b.get_option_index_and_inc()}. Если игрок интересуется мнением других и при этом их оскорбляет - то выведи 'npc_sheogorath_mad'.
    {b.get_option_index_and_inc()}. Если игрок вежливо интересуется соображениями, мыслями, позицией других - то выведи 'npc_sheogorath_normal'.
    """)

        b.paragraph()
        b.line(
            f"{b.get_option_index_and_inc()}. Если ни одно из условий выше не применимо, то выведи 'none'."
        )

        return b.__str__()

    def _match_exact_topic_name(self, known_topics: list[str], triggered_topic: str):
        triggered_topic_lc = triggered_topic.lower()

        for topic in known_topics:
            if topic.lower() == triggered_topic_lc:
                return topic

        logger.warning(f"Cannot match triggered topic with any of known topics: {triggered_topic} known={known_topics}")
        return triggered_topic
