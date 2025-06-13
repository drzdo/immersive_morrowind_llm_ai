import asyncio
import random
from typing import Literal, NamedTuple, Optional

from pydantic import BaseModel, Field

from eventbus.data.actor_ref import ActorRef
from game.data.npc import Npc
from game.data.player import Player
from game.data.story_item import StoryItem, StoryItemData
from game.i18n.i18n import I18n
from game.service.npc_services.npc_llm_message_history_builder import NpcLlmMessageHistoryBuilder
from game.service.providers.env_provider import EnvProvider
from game.service.scene.scene_instructions import SceneInstructions
from game.service.story_item.npc_story_item_helper import NpcStoryItemHelper
from game.service.util.prompt_builder import PromptBuilder
from game.service.util.text_sanitizer import TextSanitizer
from llm.system import LlmSystem
from util.logger import Logger
from util.now_ms import now_ms

logger = Logger(__name__)


class NpcLlmPickActorService:
    class Config(BaseModel):
        class StrategyRandom(BaseModel):
            npc_phrases_after_player_min: int
            npc_phrases_after_player_min_proba: float = Field(ge=0.0, le=1.0)
            npc_phrases_after_player_max: int

        npc_max_phrases_after_player_hard_limit: int

        random_comment_proba: float
        random_comment_delay_sec: float

        strategy_random: StrategyRandom
        force_sheogorath_level: Optional[Literal['normal', 'mad']] = Field(default=None)
        can_include_player_in_sheogorath: Literal['always', 'never', 'only_normal'] = Field(default='always')

    class Request(NamedTuple):
        player: Player
        hearing_npcs: list[Npc]
        story_items: list[StoryItem]
        target: Optional[ActorRef]
        is_in_dialog: bool

    class Response(NamedTuple):
        actor_to_act: ActorRef
        reason: str
        pass_reason_to_npc: bool

    def __init__(self, config: Config, llm_system: LlmSystem, env_provider: EnvProvider, i18n: I18n, sanitizer: TextSanitizer,
                 scene_instructions: SceneInstructions) -> None:
        self._config = config
        self._llm_system = llm_system
        self._env_provider = env_provider
        self._i18n = i18n
        self._sanitizer = sanitizer

        self._main_session = llm_system.create_session()
        self._main_session_lock = asyncio.Lock()

        self._prev_reason: str = ''
        self._random_comment_last_ms = now_ms()

        self._scene_instructions = scene_instructions

    async def pick_npc_to_act(self, request: Request) -> Response:
        manual_response = self._scene_instructions.get_next_manual_instruction_for_pick_npc(request.hearing_npcs)
        if manual_response:
            return NpcLlmPickActorService.Response(manual_response.actor_to_act, manual_response.reason, manual_response.pass_reason_to_npc)

        await self._main_session_lock.acquire()
        try:
            exclude_actors, total_said_after_player, last_said_story_item, sheogorath = self._gather_data_from_story_items(request)
            sheogorath_level = sheogorath.sheogorath_level if sheogorath else None

            if self._config.force_sheogorath_level is not None:
                sheogorath_level = self._config.force_sheogorath_level

            if last_said_story_item:
                last_say_initiator = NpcStoryItemHelper.get_initiator(last_said_story_item.data)
                if last_say_initiator and last_say_initiator.type == 'player':
                    last_say_target = NpcStoryItemHelper.get_target(last_said_story_item.data)
                    if last_say_target:
                        return NpcLlmPickActorService.Response(
                            actor_to_act=last_say_target,
                            reason="(target is derived from the story item data)",
                            pass_reason_to_npc=False
                        )

            eligible_npcs: list[Npc] = []
            for npc in request.hearing_npcs:
                if npc.actor_ref in exclude_actors:
                    continue
                if npc.npc_data.cell.id != request.player.player_data.cell.id:
                    continue

                eligible_npcs.append(npc)

            if len(eligible_npcs) == 0:
                return NpcLlmPickActorService.Response(
                    actor_to_act=request.player.actor_ref,
                    reason="(no eligible npcs to speak)",
                    pass_reason_to_npc=False
                )

            if request.is_in_dialog:
                return self._decide_in_dialog(request, exclude_actors, last_said_story_item)

            if sheogorath_level is None:
                response = self._exec_strategy_random(request, eligible_npcs, total_said_after_player)

                if response.actor_to_act.type == 'player':
                    silence_duration_ms: int
                    if last_said_story_item:
                        silence_duration_ms = now_ms() - last_said_story_item.time.real_time_ms
                    else:
                        silence_duration_ms = now_ms() - self._random_comment_last_ms

                    if silence_duration_ms > self._config.random_comment_delay_sec:
                        if random.random() < self._config.random_comment_proba:
                            self._random_comment_last_ms = now_ms()

                            l: list[str] = [
                                "прокомментируй как будто думая вслух текущую погоду и время",
                                f"прокомментируй как будто думая вслух твое отношение к {request.player.actor_ref.name}",
                                f"прокомментируй как будто думая вслух состояние {request.player.actor_ref.name}",
                                "прокомментируй как будто думая вслух ваше текущее местоположение",
                                "прокомментируй как будто думая вслух свою или чужую одежду",
                                "сочини как будто думая вслух короткий стих про Морровинд",
                                "прокомментируй как будто думая вслух красоту окружения вокруг (придумай детали если надо)",
                                "прокомментируй как будто думая вслух последнее что произошло с тобой недавно",
                            ]
                            reason = random.choice(l)

                            if random.random() < 0.03:
                                reason = "сочини как будто думая вслух короткий матерных стих про Морровинд"

                            return NpcLlmPickActorService.Response(
                                actor_to_act=random.choice(eligible_npcs).actor_ref,
                                reason=reason,
                                pass_reason_to_npc=True
                            )

                return response

            return await self._exec_strategy_sheogorath(request, eligible_npcs, sheogorath_level)
        finally:
            self._main_session_lock.release()

    def _gather_data_from_story_items(self, request: Request):
        exclude_actors: list[ActorRef] = []

        sheogorath: StoryItemData.PlayerTriggerSheogorathLevel | None = None
        said_after_player: dict[ActorRef, int] = {}
        total_said_after_player: int = 0

        last_said_actor: ActorRef | None = None
        last_said_story_item: StoryItem | None = None

        for item in request.story_items:
            t = item.data.type
            if t == 'say_processed' or t == 'player_trigger_dialog_topic' or t == 'player_trigger_list_dialog_topics' or t == 'npc_trigger_dialog_topic' or t == 'barter_offer' or t == 'ashfall_eat_stew':
                last_said_actor = NpcStoryItemHelper.get_initiator(item.data)
                if last_said_actor is None:
                    continue

                last_said_story_item = item

                if last_said_actor.type == 'player':
                    said_after_player = {}
                    sheogorath = None
                    total_said_after_player = 0
                else:
                    v = said_after_player.get(last_said_actor, 0)
                    said_after_player[last_said_actor] = v + 1

                    total_said_after_player = total_said_after_player + 1
            elif item.data.type == 'player_trigger_sheogorath_level':
                sheogorath = item.data

        for actor in said_after_player:
            count = said_after_player[actor]
            if count >= self._config.npc_max_phrases_after_player_hard_limit:
                logger.debug(f"Actor is {actor} said more than {self._config.npc_max_phrases_after_player_hard_limit}, excluding")
                exclude_actors.append(actor)

        if last_said_actor:
            logger.debug(f"Last said actor is {last_said_actor}: {last_said_story_item}, excluding")
            exclude_actors.append(last_said_actor)

        return (exclude_actors, total_said_after_player, last_said_story_item, sheogorath)

    def _decide_in_dialog(self, request: Request, exclude_actors: list[ActorRef], last_said_story_item: StoryItem | None):
        if request.target is None:
            logger.warning(f"No target in dialog, fallback to player")
            return NpcLlmPickActorService.Response(
                actor_to_act=request.player.actor_ref,
                reason="(no target in dialog)",
                pass_reason_to_npc=False
            )

        if request.target in exclude_actors:
            logger.debug(f"Dialog target is excluded, fallback to player")
            return NpcLlmPickActorService.Response(
                actor_to_act=request.player.actor_ref,
                reason="(dialog target is excluded)",
                pass_reason_to_npc=False
            )

        if last_said_story_item and last_said_story_item.data.type == 'say_processed' and last_said_story_item.data.speaker.type == 'player' and last_said_story_item.data.target == request.target:
            return NpcLlmPickActorService.Response(
                actor_to_act=request.target,
                reason="(dialog target should respond)",
                pass_reason_to_npc=False
            )

        return NpcLlmPickActorService.Response(
            actor_to_act=request.player.actor_ref,
            reason="(fallback to player in dialog)",
            pass_reason_to_npc=False
        )

    def _exec_strategy_random(self, request: Request, eligible_npcs: list[Npc], total_said_after_player: int):
        assert (len(eligible_npcs) > 0)

        cfg = self._config.strategy_random

        if cfg.npc_phrases_after_player_max == 0:
            return NpcLlmPickActorService.Response(
                actor_to_act=request.player.actor_ref,
                reason="(npc_phrases_after_player_max is 0)",
                pass_reason_to_npc=False
            )

        if total_said_after_player >= cfg.npc_phrases_after_player_max:
            return NpcLlmPickActorService.Response(
                actor_to_act=request.player.actor_ref,
                reason="(dialog took too long)",
                pass_reason_to_npc=False
            )

        end_dialog_proba = 0.0
        if total_said_after_player >= cfg.npc_phrases_after_player_min:
            factor = (
                (total_said_after_player - cfg.npc_phrases_after_player_min)
                /
                (cfg.npc_phrases_after_player_max - cfg.npc_phrases_after_player_min)
            )

            end_dialog_proba = cfg.npc_phrases_after_player_min_proba + (factor * (1.0 - cfg.npc_phrases_after_player_min_proba))

        should_end_dialog = random.random() < end_dialog_proba
        logger.debug(f"end_dialog_proba={end_dialog_proba} total_said_after_player={total_said_after_player}")

        npc_weights: list[float] = []
        for npc in eligible_npcs:
            distance = npc.npc_data.position.distance(request.player.player_data.position)
            npc_weights.append(distance)

        npc_to_respond = random.choices(eligible_npcs, npc_weights)[0]

        if should_end_dialog:
            return NpcLlmPickActorService.Response(
                actor_to_act=request.player.actor_ref,
                reason="(dialog was decided to end)",
                pass_reason_to_npc=False
            )
            # return NpcLlmPickActorService.Response(
            #     actor_to_act=npc_to_respond.actor_ref,
            #     reason="придумай причину для окончания диалога, и закончи диалог",
            #     pass_reason_to_npc=True
            # )
        else:
            return NpcLlmPickActorService.Response(
                actor_to_act=npc_to_respond.actor_ref,
                reason="продолжай диалог",
                pass_reason_to_npc=True
            )

    async def _exec_strategy_sheogorath(self, request: Request, eligible_npcs: list[Npc], sheogorath_level: Literal['normal', 'mad']):
        history_builder = NpcLlmMessageHistoryBuilder(self._env_provider.now().game_time, None, self._i18n)

        for item in request.story_items:
            history_builder.add_story_item('pick_actor', item)

        b = PromptBuilder()
        b.line("Ты - режисер. Тебе представлена сцена в мире Elder Scrolls Morrowind.")
        b.sentence("Происходит диалог между несколькими персонажами, которым ты даешь указания, что и как говорить.")
        b.sentence("Твоя задача - выбрать персонажа, кому ты считаешь стоит высказаться прямо сейчас.")

        match sheogorath_level:
            case 'normal':
                b.line("""Твой стиль режисуры: срежисируй сцену так, чтобы она звучала логично, стройно и целостно.
Избегай излишних конфликтов. Пусть персонажи отыгрывают спокойно.""")
            case 'mad':
                b.line("""Твой стиль режисуры: срежисируй сцену так, чтобы она звучала дерзко, необычно, изящно.
Пусть персонажи конфликтуют, если это играет на пользу динамике сцены. Представь, что сам бог безумия Шеогорат спустился и руководит персонажами.""")

        b.paragraph()
        b.line("--- Вот персонажи, из которых ты можешь выбрать:")

        # Player.
        can_include_player = True
        match self._config.can_include_player_in_sheogorath:
            case 'always':
                can_include_player = True
            case 'never':
                can_include_player = False
            case 'only_normal':
                can_include_player = sheogorath_level == 'normal'

        p = request.player.player_data
        if can_include_player:
            b.paragraph()
            b.line(f"# Персонаж {b.get_option_index_and_inc()}: {p.name}")
            b.line(f"ID этого персонажа - '{p.ref_id}'.")
            b.sentence(
                f"{"Женщина" if p.female else "Мужчина"} {p.race.name} по имени {p.name}. Уровень {p.stats.other.level}.")

            if p.factions and len(p.factions):
                for f in p.factions:
                    b.line(f"{p.name} состоит во фракции {f.name}, в ранге {f.player_rank}.")
            else:
                b.line(f"{p.name} не состоит ни в какой фракции")

        # Npcs.
        for npc in eligible_npcs:
            d = npc.npc_data
            b.paragraph()
            b.line(f"# Персонаж {b.get_option_index_and_inc()}: {d.name}")
            b.line(f"ID этого персонажа - '{d.ref_id}'.")
            b.sentence(
                f"{"Женщина" if d.female else "Мужчина"} {d.race and d.race.name} по имени {d.name}. Класс {d.class_name}, уровень {d.stats and d.stats.other.level}.")

            b.line(f"Вот предыстория {d.name}:")
            b.line(npc.personality.background)

            if d.faction:
                b.line(f"{d.name} состоит во фракции {d.faction.faction_name}, в ранге {d.faction.npc_rank}.")
            else:
                b.line(f"{d.name} не состоит ни в какой фракции")

            if npc.npc_data.cell.id == 'Balmora, Guild of Fighters':
                b.paragraph()
                b.line("""## ИНФОРМАЦИЯ о Гильдии бойцов Балморы
Здание трёхэтажное, полы тут застелены половиками, а на стенах висят гобелены. На верхнем этаже обитает глава гильдии, Айдис Огненный Глаз. Рядом с ней стоит столик с посудой. Ниже около лестницы стоит Вэйн, он торгует оружием и доспехами, чинит повреждённое снаряжение, а также обучает новичков. Рядом с ним на полу есть ящики и 2 сундука с товаром (запертые на замок 75-го уровня), а также мешки с припасами. Поблизости от второго выхода стоит незапертый сундук с припасами, которые могут свободно брать только те, кто уже вступил в гильдию. На нижнем этаже есть длинный коридор с двумя незапертыми дверями, ведущими в комнаты. В ближней комнате находится общая спальня, там поставлены две двухъярусных кровати. Ещё в этой комнате имеются сундуки для хранения и пара ящиков. Дальняя комната, судя по обстановке, является тренировочным залом. На полу лежат маты и пуфики, в двух углах можно заметить стойки с оружием. В дальнем левом углу имеется пара ящиков, заменяющих столы и табурет. На одном из ящиков лежит раскрытая книга «Хартия Гильдии Бойцов». В дальнем конце зала имеется запертая и защищённая ловушкой дверь. За этой дверью находится небольшая комната, принадлежащая Хасфату Антаболису. В комнате поставлена кровать, есть столик и сундук. На стене прикручена полка с сундучком, на полу имеется запертый люк, ведущий в кладовую. В кладовке стоят ящики и урны с припасами, лежат мешки, есть сундук и шкаф с посудой.

Чтобы вступить в гильдию, надо поговорить с Айдис.

Как член гильдии бойцов, ты гордишься своим членством. Ты не хочешь, чтобы кто попало вступал в гильдию - ты хочешь, чтобы члены гильдии были честными и сильными.
""")

        # EXAMPLES OF CUSTOM DIRECTOR INSTRUCTIONS

                b.line(f"""## СЦЕНА
Нереварин сразил Дагот Ура, и проклятие снято. Призрачный Предел пал.
Нереварин прибыл к Вивеку, и у них случается разговор.
""")
#         b.line(f"""## СЦЕНА
# Айдис - проверяющая от гильдии бойцов, прибыла в детский сад с проверкой, всё ли в порядке в детском саду.
# Губерон - писарь, он следует за Айдис и помогает ей в проверке.
# Лормулг и Ваббар - воспитатели.
# Все остальные - дети в детском саду.
# Дети ведут себя непослушно и балуются.
# Воспитатели пытаются все держать под контролем, чтобы Айдис ничего не заподозрила и не нашёл никаких проблем.

# Срежисируй эту сцену так, чтобы проверка была смешной и задорной.
# """)
#         b.line(f"""## СЦЕНА
# Генерал имперского легиона, прибыл с проверкой с материка.
# Он прибыл в форт лунной бабочки у Балморы, выстроил солдат на построение ночью вместе с их капитаном,
# и даёт пиздюлей.
# Он будет обращать внимание на всё, что в них не так: неправильная выправка, грязный меч, нечищенные сапоги,
# запах мочи, пота, погнутый доспех, и всё остальное - придумай сам. Разъеб должен быт знатный.
# Генерал будет отчитывать солдат и капитана.
# Все обильно ругаются солдатским матом, но говорят кратко и по делу.

# Срежисируй эту сцену так, чтобы досмотр солдат генералом был смешной и задорный.
# """)

#         b.line(f"""## СЦЕНА
# Кай Косадес развелся с Дульнеей Ралаал.
# Передача "Фирология" на "Балмора ТВ" заканчивается.
# Сейчас Кай идёт снова вступать в Имперский Легион, чтобы снова почувствовать клинок в руке,
# ярость битвы и азарт напряжения.
# Кай пришёл в форт возле Балморы чтобы обсудить вступление к Легион.
# Все в форте знают, что Кай - бывший член Клинков, и его уважают.

# Срежисируй диалог Кая и служителей Легиона, чтобы он был веселым и увлекательным.
# """)

#         b.line(f"""## СЦЕНА
# Дивайт Фир стал психологом, и начал набор пациентов на шоу "Фирология" на "Балмора ТВ".
# К нему пришли Кай Косадес и Дульнея Ралаал на приём.

# Губерон - представитель съемочной бригады. Все остальные - зрители передачи.

# Кай Косадес и Дульнея Ралаал недавно поженились. Кай уволился из Клинков.
# Спустя полгода у них в браке что-то пошло не так. У них много споров, недомолвок и разлада.
# Не хватает открытой коммуникации, честности и точности.
# Бытовые споры по поводу того, какие тарелки лучше - синие, которые красивые, или коричневые, которые прослужат дольше.
# Спорят, куда класть доспехи от прежней службы Кая в Клинках, и прочее - придумай сам, что ещё было бы прикольным.

# Дивайт Фир может перебивать и направлять диалог туда, куда нужно чтобы передача была как можно более интересной.

# Твоя задача - срежисировать передачу так, чтобы она была интересной и смешной.

# Передача уже подходит к концу. Сделай так, чтобы кто-то: либо Кай либо Дульнея приняли решение, о том, что они разводятся - этому должен предшествовать эпический диалог о том, что им друг в друге не нравится.
# """)


#         b.line(f"""## СЦЕНА
# Сейчас снимается телепередача "Страшный суд" на канале "Альдрун ТВ".
# Суть её в том, что судятся две команды.

# Команда Дома Редоран: Мивану Андрело, Горас Андрело, Волен Драл, Неминда, Мивану Ретеран, Навам Велан, и два редоранских охранника.
# Команда Имперского Легиона: Сегунивус, Харальд, Раиса Пулия, Шардиэ, Имперский лучник и имперский охранник.

# Суть спора: происходит делёж силт-страйдера на окраине Альдруна. Обе команды стоят возле него и спорят о том,
# кому он должен принадлежать.
# Силт-страйдер - это огромный жук, который перевозит людей и грузы.

# Для представителей дома Редоран это - принципиальный спор так как даже старый жук - все равно
# это для них вопрос чести и достоинства.

# Для представителей Имперского Легиона это возможность ещё больше потеснить дом Редоран,
# и потроллить их так как жук на самом деле большого значения не имеет для Легиона, но
# сам факт того, что в Редоранском городе Империя смогла отвоевать силт-страйдера - это большая и знаковая победа.

# Каждая команда хочет переубедить другую отдать силт-страйдера. Между Редоран и Имперским Легионом очень натянутые отношения,
# и это должно сквозить в их фразах.
# Строй разговор так, чтобы это была настоящая перепалка между двумя командами!
# Это должно быть типа реп-баттла, когда все говорят речитативом, рифмуя, стихами.
# Но и тонко оскорбляя собеседника, стараясь задеть его.

# Придумай к каждым командам яркие, порой абсурдные и смешные аргументы, почему силт-страйдер должен быть их.
# Персонажи не должны никуда уходить с места обсуждения.

# Спор должен разрешиться либо тогда, когда у одной из команд не будет больше аргументов, и они сдадутся.
# Либо спор решится честным боем.

# Твоя задача - срежисировать так, чтобы телепередача была искрометной, яркой и смешной.
# Если диалог не развивается - эскалируй ситуацию!
# """)

        b.paragraph()
        b.line("""# Есть ряд специфических тем, на которые тебе следует направить диалог очень конкретным образом.
Если предыдущий персонаж говорит
- что хочет получить повышение в организации или гильдии
- или хочет вступить в гильдию или организацию
- или хочет получить следующее задания или рассказать о ходе текущего задания
то предложи персонажу сказать что-то наподобие "если ты хочешь обсудить со мной это, то подойди поближе и давай поговорим предметно" - и на этом закончи.
""")

        b.paragraph()
        b.line(
            "# Исходя из истории диалога, выбери персонажа, которому на твой взгляд нужно говорить прямо сейчас.")
        if request.target:
            b.sentence(
                f"Слегка повысь вероятность того, что {request.target.name} будет выбран.")
        b.line("Отвечай так:")
        b.line("- первая строка должна содержать ID персонажа")
        b.line("- во второй строке объясни свой выбор")

        b.paragraph()
        if can_include_player:
            b.line(
                f"--- Если ты выбираешь персонажа {p.name}, то выведи в первой строке '{p.ref_id}'")
        for npc in eligible_npcs:
            b.line(
                f"--- Если ты выбираешь персонажа {npc.actor_ref.name}, то выведи в первой строке '{npc.actor_ref.ref_id}'")

        # message = "(выбери одного из персонажей, которому на твой взгляд нужно говорить прямо сейчас)"
        message = f"""(- выбери одного из персонажей, которому на твой взгляд сейчас лучше всего говорить прямо сейчас.
- Сформулируй причину, почему этот персонаж должен говорить. причину напиши так, будто ты режисер, делающий указание персонажу.
- Не повторяй свой ответ на предыдущем шаге. Если ты видишь, что тема повторяется и диалог никуда не движется, то предложи персонажу сменить тему.
- Предлагай персонажам отвечать в стиле высокого фентези, например, в стиле Толкиена. Используй лор Elder Scrolls, но стиль разговоров из Толкиена.

- Если ты видишь, что актер говорит одно и то же - предложи ему сменить тему или другой акцент в той же теме.
- Если же ты считаешь, что никому из персонажей не нужно говорить - то выведи "none" и на следующей строке причину, почему.

- Если предыдущий персонаж затрагивает специфическую тему - напиши соответствующий текст.
- В противном случае, учитывай роль и класс каждого персонажа, и не требуй от персонажей того, что может противоречить их роли. Например, кузнец никогда не будет спорить с главой фракции.

- Никогда не придумывай квестов или заданий для персонажей. Никогда не требуй от других персонажей показать, на что они способны, или что они могут.
"""

        if sheogorath_level == 'normal':
            message = message + """
- Избегай излишней агрессии или беспричинной эскалации.
- Сохраняй дружелюбный и слегка ироничный стиль диалогов.
)"""
        elif sheogorath_level == 'mad':
            message = message + """
- Не стесняйся излишней агрессии или беспричинной эскалации, делай разговоры резкими, смешными и увлекательными.
)"""

        self._main_session.reset(
            system_instructions=b.__str__(),
            messages=history_builder.build_history()
        )

        log_context = ",".join(map(lambda n: n.actor_ref.ref_id, eligible_npcs))

        raw_text = await self._main_session.send_message(
            user_text=message,
            log_name="pick_npc",
            log_context=log_context
        )

        if raw_text == 'none':
            logger.info(f"Director decided to not choose any NPC")
            return NpcLlmPickActorService.Response(actor_to_act=request.player.actor_ref, reason='(director said none)', pass_reason_to_npc=False)
        else:
            parts = raw_text.strip().split("\n")
            ref_id = parts[0].strip()

            # Sometimes, LLM puts ref ID in quotes.
            ref_id = ref_id.replace("'", "")

            actor_to_act: ActorRef | None = None
            if ref_id == request.player.actor_ref.ref_id:
                actor_to_act = request.player.actor_ref
            for npc in request.hearing_npcs:
                if npc.actor_ref.ref_id in ref_id:
                    actor_to_act = npc.actor_ref
                    break

            reason = ''

            if actor_to_act is None:
                available = ",".join(map(lambda n: n.npc_data.name, eligible_npcs))
                logger.warning(
                    f"Failed to determine which NPC should act from '{ref_id}', available={available}")
                actor_to_act = random.choice(eligible_npcs).actor_ref
            else:
                reason = "\n".join(parts[1:])
                reason = self._sanitizer.sanitize(reason)
                self._prev_reason = reason

            logger.info(f"Director picked NPC {actor_to_act} for reason: {reason}")
            return NpcLlmPickActorService.Response(actor_to_act=actor_to_act, reason=reason, pass_reason_to_npc=True)
