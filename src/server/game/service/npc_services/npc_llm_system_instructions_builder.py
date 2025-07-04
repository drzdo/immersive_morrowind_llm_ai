import math
from eventbus.data.actor_stats import ActorStats
from eventbus.data.npc_data import NpcData
from game.data.npc import Npc
from game.i18n.i18n import I18n
from game.service.npc_services.npc_spawn_list import NPC_SPAWN_LIST
from game.service.player_services.player_provider import PlayerProvider
from game.service.providers.cell_name_provider import CellNameProvider
from game.service.providers.dropped_items_provider import DroppedItemsProvider
from game.service.providers.env_provider import EnvProvider
from game.service.scene.scene_instructions import SceneInstructions
from game.service.util.format_date import format_date
from game.service.util.map_value_in_range import map_value_in_range
from game.service.util.prompt_builder import PromptBuilder
from llm.message import LlmMessage
from util.distance import Distance
from util.logger import Logger

logger = Logger(__name__)


class NpcLlmSystemInstructionsBuilder():
    def __init__(self, player_provider: PlayerProvider, env_provider: EnvProvider,
                 dropped_items_provider: DroppedItemsProvider,
                 cell_name_provider: CellNameProvider, i18n: I18n,
                 scene_instructions: SceneInstructions):
        self._player_provider = player_provider
        self._env_provider = env_provider
        self._dropped_items_provider = dropped_items_provider
        self._cell_name_provider = cell_name_provider
        self._i18n = i18n
        self._scene_instructions = scene_instructions

    def build(self, npc: Npc, other_npcs: list[Npc], messages: list[LlmMessage]) -> str:
        b = PromptBuilder()
        d = npc.npc_data

        self._initial(npc, b, d)
        self._what_npc_does(b, d)
        self._current_env(b, d)
        self._health(b, d)
        self._npcs_nearby(npc, b, d, other_npcs)
        self._player_info(npc, b, d)
        self._info_from_wiki(npc, b, d)
        self._final(npc, b, d, other_npcs, messages)

        return b.__str__()

    def _initial(self, npc: Npc, b: PromptBuilder, d: NpcData) -> None:
        b.paragraph()
        # b.new_line("Ты - актер в театре импровизации, играющий персонажа во вселенной игры Morrowind из Elder Scrolls. Используй лор Elder Scrolls.")
        # b.new_line(f"Твоего персонажа зовут {d.name}. Это {"женщина" if d.female else "мужчина"} расы {d.race.name}.")

        b.line("""Ты - персонаж во вселенной игры Morrowind из Elder Scrolls.
""")
        race_name = d.race.name if d.race else "неизвестной"
        if npc.actor_ref.ref_id == 'vivec_god00000000':
            race_name = "каймер"

        b.line(f"Тебя зовут {d.name}, ты - {"женщина" if d.female else "мужчина"} расы {race_name}.")

        b.paragraph()
        b.line("# ТВОЯ ПРЕДЫСТОРИЯ")
        b.line(npc.personality.background)

        b.paragraph()
        b.line("# ИНФОРМАЦИЯ О ТЕБЕ")
        b.line(f"Класс персонажа - {d.class_name}")
        if d.stats:
            self._sentence_with_top_skills(b, True, d.female, d.stats)

        if d.faction:
            b.line(f"{d.name} состоит во фракции {d.faction.faction_name}, твой ранг {d.faction.npc_rank}.")
        else:
            b.line(f"{d.name} не состоит ни в какой фракции")

        b.line()
        if len(d.equipped) > 0:
            names = map(lambda v: v.name, d.equipped)
            b.sentence(f'На {d.name} надето: {",".join(names)}')
        else:
            b.sentence(f'На {d.name} ничего не надето')

        if d.nakedness.head:
            b.sentence(f"У {d.name} не покрыта голова")
        if d.nakedness.feet:
            b.sentence(f"{d.name} босой")
        if d.nakedness.legs:
            b.sentence(f"На {d.name} нет штанов")
        if d.nakedness.torso:
            b.sentence(f"У {d.name} голый торс")

    def _what_npc_does(self, b: PromptBuilder, d: NpcData) -> None:
        b.paragraph()

        is_inntrader = (d.class_name in ["Трактирщик"]) or d.is_ashfall_innkeeper
        barters: list[str] = []
        services: list[str] = []

        ai = d.ai_config
        if ai.barters_alchemy:
            barters.append("напитками" if is_inntrader else "зельями")
        if ai.barters_apparatus:
            barters.append("приспособлениями для варения зелий")
        if ai.barters_armor:
            barters.append("броней")
        if ai.barters_books:
            barters.append("книгами")
        if ai.barters_clothing:
            barters.append("одеждой")
        if ai.barters_enchanted_items:
            barters.append("зачарованными вещами")
        if ai.barters_ingredients:
            barters.append("едой" if is_inntrader else "ингридиентами")
        if ai.barters_lights:
            barters.append("факелами и фонарями")
        if ai.barters_lockpicks:
            barters.append("отмычками для отпирания дверей")
        if ai.barters_lockpicks:
            barters.append("щупами для обезвреживания ловушек")
        if ai.barters_repair_tools:
            barters.append("кузнечными молотами для починки оружия и брони")
        if ai.barters_weapons:
            barters.append("оружием")

        if ai.offers_bartering:
            barters.append("покупает и продает")
        if ai.offers_enchanting:
            barters.append("оказывает услуги по зачарованию предметов")
        if ai.offers_repairs:
            barters.append("чинит оружие и броню")
        if ai.offers_spellmaking:
            barters.append("оказывает услуги по созданию заклинаний")
        if ai.offers_spells:
            barters.append("продает заклинания")
        if ai.offers_training:
            barters.append("оказывает услуги персонального тренера по некоторым навыкам")
        if ai.travel_destinations and len(ai.travel_destinations) > 0:
            towhere = ",".join(map(lambda d: self._cell_name_provider.get_cell_name(d), ai.travel_destinations))
            barters.append(f"оказывает услуги по перемещению в {towhere}")

        if len(barters) > 0:
            b.sentence(f"{d.name} торгует {",".join(barters)}.")
        if len(services) > 0:
            b.sentence(f"{d.name} {",".join(services)}.")

        if is_inntrader:
            if d.ashfall_stew_cost:
                b.sentence(f"{d.name} продает супы и рагу.")
            else:
                b.sentence(f"{d.name} продает супы и рагу. Суп или рагу стоит {d.ashfall_stew_cost} монет.")

    def _current_env(self, b: PromptBuilder, d: NpcData) -> None:
        b.paragraph()

        env = self._env_provider.env

        today = format_date(env.current_day, env.current_month, env.current_year)
        b.sentence(f"Дата в сценарии - {today}")

        gametime_h = math.floor(env.current_hour)

        daypart = 'день'
        if gametime_h < 5 or gametime_h >= 21:
            daypart = "ночь"
        if gametime_h >= 5 and gametime_h < 7:
            daypart = "рассвет"
        if gametime_h >= 7 and gametime_h < 11:
            daypart = "утро"
        if gametime_h >= 11 and gametime_h < 14:
            daypart = "полдень"
        if gametime_h >= 14 and gametime_h < 18:
            daypart = "день"
        if gametime_h >= 18 and gametime_h < 21:
            daypart = "вечер"

        b.sentence(f"Текущее время: {self._i18n.format_time(env.current_hour)}, {daypart}.")
        b.sentence(f"Текущая погода: {env.current_weather}.")

        if env.ashfall:
            map_value_in_range(
                env.ashfall.weatherTemp, "Температура воздуха снаружи {}", -100, 100,
                ["чрезвычайно холодная", "очень холодная", "холодная", "прохладная",
                 "комфортная", "комфортная",
                 "теплая", "жаркая", "очень жаркая", "чрезвычайно высокая"]
            )

        b.sentence(f"Солнце встает в {self._i18n.format_time(env.sunrise_hour)}.")
        b.sentence(f"Солнце садится в {self._i18n.format_time(env.sunset_hour)}.")

        if env.masser_phase is not None and env.secunda_phase is not None:
            b.sentence("На небе есть две луны: Массер и Секунда.")
            b.sentence(self._get_formatted_moon_phase("Массер", env.masser_phase))
            b.sentence(self._get_formatted_moon_phase("Секунда", env.secunda_phase))

        b.line(f"{d.name} сейчас находится в {self._cell_name_provider.get_cell_name(d.cell.name or d.cell.id)}.")

    def _get_formatted_moon_phase(self, moon_name: str, phase_num: int):
        # Новолуние — Луна не видна на небе.
        # Молодая Луна (Растущий месяц) — первое появление Луны на небе после новолуния, узкий серп.
        # Первая четверть — освещена половина Луны.
        # Растущая Луна — освещена большая часть Луны.
        # Полнолуние — освещена вся Луна целиком.
        # Убывающая Луна — освещена большая часть Луны, но с другой стороны.
        # Последняя четверть — освещена другая половина Луны.
        # Старая Луна (Убывающий месяц) — освещён узкий серп Луны с другой стороны, предшествует Новолунию.
        if phase_num == 0:
            return f"Сейчас новолуние у луны {moon_name}, ее не видно."
        if phase_num == 1:
            return f"Сейчас луна {moon_name} молодая, видна как узкий серп на небе."
        if phase_num == 2:
            return f"Сейчас луна {moon_name} в первой четверти, видна её половина."
        if phase_num == 3:
            return f"Сейчас луна {moon_name} растущая, видна бОльшая ее часть."
        if phase_num == 4:
            return f"Сейчас полнолуние у луны {moon_name}."
        if phase_num == 5:
            return f"Сейчас луна {moon_name} убывает, видна бОльшая ее часть."
        if phase_num == 6:
            return f"Сейчас луна {moon_name} в последней четверти, видна ее другая половина."
        if phase_num == 7:
            return f"Сейчас луна {moon_name} старая, виден лишь узкий ее серп с другой стороны. Предшествует новолунию."
        return f"Луна {moon_name} не видна так как я в помещении."

    def _health(self, b: PromptBuilder, d: NpcData):
        b.paragraph()
        if d.in_combat:
            if len(d.hostiles) > 0:
                names = map(lambda v: v.name, d.hostiles)
                hostiles = ",".join(names)
                b.line(f"У {d.name} прямо сейчас сражение с такими противниками как {hostiles}.")

        b.line(map_value_in_range(
            d.health_normalized, "{}", 0, 100,
            [f"{d.name} очень ранен и при смерти", f"У {d.name} сильное ранение", f"{
                d.name} ранен", f"{d.name} легко ранен", f"У {d.name} нет ранений"]
        ))
        if d.is_diseased:
            b.line(f"{d.name} заболел.")

    def _npcs_nearby(self, npc: Npc, b: PromptBuilder, d: NpcData, other_npcs: list[Npc]):
        b.paragraph()
        for other_npc in other_npcs:
            self._other_npc_summary(npc, b, d, other_npc)

    def _other_npc_summary(self, npc: Npc, b: PromptBuilder, d: NpcData, other_npc: Npc):
        d2 = other_npc.npc_data

        distance_ingame = other_npc.npc_data.position.distance(d.position)
        distance_meters = Distance.from_ingame_to_meters(distance_ingame)

        he = "она" if d2.female else "он"
        him = "неё" if d2.female else "него"
        verb_suffix = "а" if d2.female else ""

        b.line()
        b.sentence(
            f"- В {round(distance_meters)} метров от {d.name} стоит {"женщина" if d2.female else "мужчина"} {d2.race.name if d2.race else ""} по имени {d2.name}")
        if d2.stats:
            b.sentence(f"У {him} уровень {d2.stats.other.level}, класс {d2.class_name}.")

        disposition_to_other_npc = npc.behavior.relation_to_other_npc.get(other_npc.actor_ref.ref_id, 50)
        b.sentence(map_value_in_range(
            disposition_to_other_npc, f"Ты относишься к {d2.name} {"{}"}.", 0, 100,
            ["чрезвычайно плохо", "плохо", "нормально", "хорошо", "очень хорошо"]
        ))
        b.sentence(f"{he} одет{verb_suffix} в {",".join(map(lambda e: e.name, d2.equipped))}.")
        if d2.faction:
            b.sentence(f"{he} состоит во фракции {d2.faction.faction_name}.")

            if d.faction and d.faction.faction_id == d2.faction.faction_id:
                if d.faction.npc_rank == d2.faction.npc_rank:
                    b.sentence(f"{d.name} и {d2.name} одинакового ранга во фракции {d2.faction.faction_name}")
                elif d2.faction.npc_rank > d.faction.npc_rank:
                    delta = d2.faction.npc_rank - d.faction.npc_rank
                    b.sentence(
                        f"{d2.name} выше {d.name} по рангу во фракции {d2.faction.faction_name} на {delta} званий")
                else:
                    delta = d.faction.npc_rank - d2.faction.npc_rank
                    b.sentence(
                        f"{d2.name} ниже {d.name} по рангу во фракции {d2.faction.faction_name} на {delta} званий")

        if len(d2.hostiles) > 0:
            hostiles = ", ".join(map(lambda a: a.name, d2.hostiles))
            b.sentence(f"{d.name} видит, что {d2.name} прямо сейчас сражается с {hostiles}.")

        if d2.stats:
            self._sentence_with_top_skills(b, False, d2.female, d2.stats)

    def _sentence_with_top_skills(self, b: PromptBuilder, is_it_me: bool, female: bool, stats: ActorStats):
        l: list[str] = []

        def reg(name: str, value: int, bad: str, good: str):
            if value >= 80:
                l.append(f"очень {good} ({name} {value})")
            elif value <= 20:
                l.append(f"очень {bad} ({name} {value})")

        reg("сила", stats.attributes.strength, "слабый", "сильный")
        reg("интеллект", stats.attributes.intelligence, "глупый", "умный")
        reg("ловкость", stats.attributes.agility, "неловкий", "ловкий")
        reg("выносливость", stats.attributes.endurance, "невыносливый", "выносливый")
        reg("привлекательность", stats.attributes.personality, "уродливый", "привлекательный")
        reg("удача", stats.attributes.luck, "неудачливый", "удачливый")
        reg("скорость", stats.attributes.speed, "медленный", "быстрый")
        reg("сила воли", stats.attributes.willpower, "безвольный", "волевой")

        def reg2(name: str, value: int):
            if value >= 80:
                l.append(f"очень хорош{"а" if female else ""} в навыке {name} ({value})")
            elif value >= 60:
                l.append(f"достаточно хорош{"а" if female else ""} в навыке {name} ({value})")
            # elif value <= 20:
            #     l.append(f"очень плох{"а" if female else ""} в навыке {name} ({value})")

        reg2("акробатика", stats.skills.acrobatics)
        reg2("алхимия", stats.skills.alchemy)
        reg2("магия изменения", stats.skills.alteration)
        reg2("навык чинить броню", stats.skills.armorer)
        reg2("атлетика", stats.skills.athletics)

        reg2("топоры", stats.skills.axe)
        reg2("блокирование щитом", stats.skills.block)
        reg2("дробящее оружие", stats.skills.blunt_weapon)
        reg2("магия призывания", stats.skills.conjuration)
        reg2("магия разрушения", stats.skills.destruction)

        reg2("зачарование", stats.skills.enchant)
        reg2("рукопашный бой", stats.skills.hand_to_hand)
        reg2("тяжелая броня", stats.skills.heavy_armor)
        reg2("магия иллюзии", stats.skills.illusion)
        reg2("легкая броня", stats.skills.light_armor)

        reg2("длинные мечи", stats.skills.long_blade)
        reg2("стрельба из лука", stats.skills.marksman)
        reg2("средняя броня", stats.skills.medium_armor)
        reg2("торговля", stats.skills.mercantile)
        reg2("мистицизм", stats.skills.mysticism)

        reg2("магия восстановления", stats.skills.restoration)
        reg2("взлом замков", stats.skills.security)
        reg2("короткие клинки", stats.skills.short_blade)
        reg2("красться", stats.skills.sneak)
        reg2("древковое оружие", stats.skills.spear)

        reg2("убеждение", stats.skills.speechcraft)
        reg2("бой без доспехов", stats.skills.unarmored)

        if female:
            l = list(map(
                lambda s: s.replace("ый", "ая").replace("ой", "ая").replace("ий", "ая"),
                l
            ))

        he = "Я"
        if not is_it_me:
            he = "Она" if female else "Он"
        if len(l) > 0:
            b.sentence(f"{he} {", ".join(l)}")

    def _player_info(self, npc: Npc, b: PromptBuilder, d: NpcData):
        b.paragraph()

        p = self._player_provider.local_player.player_data
        logger.debug(f"Building player info from {p}")
        e = self._env_provider.env

        him_her = "ее" if p.female else "его"
        distance_m = Distance.from_ingame_to_meters(d.player_distance)

        b.line(
            f"В {round(distance_m)} метров от {d.name} стоит {"женщина" if p.female else "мужчина"} {p.race.name}.")
        b.sentence(f"{him_her} зовут {p.name}.")
        b.sentence(f"{him_her} уровень {p.stats.other.level}.")
        self._sentence_with_top_skills(b, False, p.female, p.stats)

        if d.race and d.race.id == 'Dark Elf':
            b.sentence(
                f"{d.name} понимает, что {p.name} не отсюда: {p.name} чужестранец, н'вах, чужеземец, приезжий, понаехавший, неместный.")

        if len(p.hostiles) > 0:
            hostiles = ", ".join(map(lambda a: a.name, p.hostiles))
            b.line(f"{d.name} видит, что {p.name} прямо сейчас сражается с {hostiles}.")

        for f in p.factions:
            if d.faction and d.faction.faction_id == f.faction_id:
                if f.player_expelled:
                    b.line(f"""{p.name} тоже состоял во фракции {
                        f.name}, но {him_her} изгнали за нарушение кодекса фракции.""")
                else:
                    b.line(f"{d.name} и {p.name} оба состоите в состоите во фракции {f.name}.")

                    if f.player_rank > d.faction.npc_rank:
                        b.line(f"{p.name} выше {d.name} по рангу во фракции {f.name}")
                    elif f.player_rank < d.faction.npc_rank:
                        b.line(f"{p.name} ниже {d.name} по рангу во фракции {f.name}")
                    else:
                        b.line(f"{d.name} и {p.name} одного и того же ранга во фракции {f.name}")
            else:
                if f.player_expelled:
                    b.line(f"{p.name} состоял во фракции {f.name}, но его изгнали за нарушение кодекса фракции.")
                else:
                    b.line(f"{p.name} состоит во фракции {f.name}.")

        equipped: list[str] = list(map(lambda v: v.name, p.equipped))
        if len(equipped) > 0:
            b.line(f"На {p.name} надето: {",".join(equipped)}")

        if p.nakedness.feet:
            b.sentence(f"{p.name} босой.")
        if p.nakedness.head:
            b.sentence(f"{p.name} не имеет шлема или головного убора, голова непокрыта.")
        if p.nakedness.legs:
            b.sentence(f"{p.name} ходит без штанов.")
        if p.nakedness.torso:
            b.sentence(f"{p.name} ходит с голым торсом.")
        if p.nakedness.torso and p.nakedness.head and p.nakedness.legs:
            b.sentence(f"{p.name} ходит полностью голышом.")

        if p.weapon_drawn:
            if p.weapon:
                b.line(f"{p.name} говорит с {d.name}, обнажив {p.weapon.name}.")
            else:
                b.line(f"{p.name} говорит с {d.name}, став в боевую стойку с кулаками наготове.")
        else:
            if p.weapon:
                b.line(f"{d.name} видит, что у {p.name} есть оружие {p.weapon.name}.")
            else:
                b.line(f"{d.name} видит, что {p.name} нет оружия.")

        b.line(map_value_in_range(
            d.disposition, f"{d.name} относится к {p.name} {"{}"}.", 0, 100,
            ["чрезвычайно плохо", "плохо", "нормально", "хорошо", "очень хорошо"]
        ))
        b.line(map_value_in_range(
            p.health_normalized, f"{p.name} {"{}"}", 0, 100,
            ["очень ранен и при смерти", "сильно ранен", "ранен",
             "легко ранен", "не ранен"]
        ))

        if e.ashfall:
            b.line()
            b.sentence(map_value_in_range(
                e.ashfall.thirst, f"{p.name} {"{}"}", 0, 100,
                ["не испытывает жажду", "слегка хочет пить", "хочет пить",
                 "очень хочет пить", "испытывает обезвоживание"]
            ))
            b.sentence(map_value_in_range(
                e.ashfall.hunger, f"{p.name} {"{}"}", 0, 100,
                ["сыт", "немного хочет есть", "хочет есть",
                 "очень хочет есть", "испытывает большой голод"]
            ))
            b.sentence(map_value_in_range(
                e.ashfall.tiredness, f"{p.name} {"{}"}", 0, 100,
                ["бодр", "отдохнул", "устал", "очень устал", "измучен и чрезвычайно устал"]
            ))
            b.sentence(map_value_in_range(
                e.ashfall.temp, "{}", -100, 100,
                [f"{p.name} замерзает", f"{p.name} очень холодно", f"{p.name} холодно", f"{p.name} прохладно",
                 f"{p.name} комфортно в плане температуры", f"{p.name} комфортно в плане температуры",
                 f"{p.name} тепло", f"{p.name} жарко", f"{p.name} очень жарко", f"{p.name} под изнуряющим палящим зноем"]
            ))

            if e.ashfall.foodPoison > 60:
                b.sentence(map_value_in_range(
                    e.ashfall.foodPoison, f"{p.name} {"{}"}.", 0, 100,
                    ["ничем не отравлен", "ничем не отравлен", "ничем не отравлен", "как будто бы чем-то траванулся",
                     "получил пищевое отравление"]
                ))

            if e.ashfall.dysentery > 60:
                b.sentence(map_value_in_range(
                    e.ashfall.dysentery, f"{p.name} {"{}"}.", 0, 100,
                    ["ничем не отравлен", "ничем не отравлен", "ничем не отравлен", "как будто бы чем-то траванулся",
                     "подхватил дизентерию"]
                ))

            if e.ashfall.flu > 60:
                b.sentence(map_value_in_range(
                    e.ashfall.flu, f"{p.name} {"{}"}.", 0, 100,
                    ["ничем не болен", "ничем не болен", "ничем не болен", "как будто бы простудился",
                     "болен простудой"]
                ))

            b.sentence(map_value_in_range(
                e.ashfall.wetness, f"{p.name} {"{}"}", 0, 100,
                ["сухой", "слегка намок", "мокрый", "промокший насквозь"]
            ))

            if e.ashfall.nearCampfire:
                b.sentence(f"{p.name} и {d.name} находитесь у костра.")

            if e.ashfall.isSheltered:
                b.sentence(f"{p.name} и {d.name} не находитесь под прямым воздействием осадков.")

        if d.following:
            b.line(f"{d.name} сейчас следует за {d.following.name}")

    def _info_from_wiki(self, npc: Npc, b: PromptBuilder, d: NpcData):
        # TODO: replace hardcore with external storage
        # Copied from
        # https://elderscrolls.fandom.com/ru/wiki/%D0%93%D0%B8%D0%BB%D1%8C%D0%B4%D0%B8%D1%8F_%D0%B1%D0%BE%D0%B9%D1%86%D0%BE%D0%B2_%D0%91%D0%B0%D0%BB%D0%BC%D0%BE%D1%80%D1%8B

        if 'chargen' in npc.actor_ref.ref_id.lower():
            p = self._player_provider.local_player.player_data
            if 'guard' in npc.actor_ref.ref_id.lower():
                b.paragraph()
                b.line(
                    f"""# Ты - стражник на тюремном корабле. Твоя задача - спокойно поприветствовать {p.name}, и пусть он дальше идёт регистрироваться в здание Имперской Канцелярии.""")
            if 'name' in npc.actor_ref.ref_id.lower():
                b.paragraph()
                b.line(
                    f"""# Ты - Джиуб, неизвестный узник тюремного корабля имперцев. Никто не знает, кто ты и за что ты арестован.""")
            if 'captain' in npc.actor_ref.ref_id.lower():
                b.paragraph()
                b.line(
                    f"""# Ты - главный начальник Имперского Легиона тут в Сейда-Нин. Твоя задача - выдать {p.name} деньги и направить его к Каю Косадесу.""")
            if 'class' in npc.actor_ref.ref_id.lower():
                b.paragraph()
                b.line(
                    f"""# Ты - заведующий Имперской Канцелярией. Твоя задача - зарегистрировать {p.name} и выдать ему паспорт.""")

        if 'Seyda Neen' in npc.npc_data.cell.id:
            b.paragraph()
            b.line("""# ИНФОРМАЦИЯ О СЕЙДА НИН
Сейда Нин — это небольшое портовое поселение на берегу Внутреннего моря, на юго-западе Вварденфелла в регионе Горький берег, в которое заходят суда с континентальной части Морровинда, а также из многих других портов Тамриэля. Кроме того, именно здесь находится единственный маяк на всём острове. Из-за своей функции главного порта региона, соединяющего весь остров с внешним миром, его нередко называют ещё и «Вратами в Вварденфелл». Всё это делает из этого поселения важнейшим портом, через который проходит множество товаров и путешественников, прибывающих на остров. Все корабли с материка сначала швартуются в местном порту, а затем большинство путешественников из Империи высаживаются и следуют в имперскую канцелярию для проверки документов. Также выгружаются и проверяются товары, для хранения которых в поселении создан целый склад, находящийся под юрисдикцией Имперского легиона.

Береговая охрана же, состоящая в основном из легионеров, преследует контрабандистов и пиратов, для которых данный регион является своеобразным домом. Впрочем, кое-кто из местных всё же жалуются на стражу в поселении.

Функция главных врат во внешний мир для всего острова привела к тому, что в отличие от других городов Горького берега, в Сейда Нин проживает большое количество чужеземцев, а его архитектура отличается более ярко выраженным «континентальным» имперским стилем. Местная имперская канцелярия позволяет отслеживать преступную деятельность на «Побережье контрабандистов», а также регистрировать всех людей и товары, проходящих через порт. Общее качество жизни кажется ниже, чем в регионе Аскадийских островов, но всё же намного лучше, чем в других поселениях Горького берега. Многие люди, чаще всего чужеземцы, живут в маленьких домиках в сиродильском стиле. Другая половина города, в основном данмеры, живут в хижинах и лачугах, формируя, тем самым, наиболее бедную часть поселения, который вкупе с близлежащими болотами и трясинами создаёт угнетающую атмосферу трущоб.

Большая часть города расположена на маленьком островке, соединённом с материком коротким пешеходным мостом. Впрочем, мост тот выполняет чисто символическую функцию, поскольку вода, разделяющая остров, мелкая и при желании и необходимости легко преодолевается вброд. В северной части острова, которая немного возвышается над уровнем остальной части островка, находятся имперская канцелярия, единственный в округе трактир и жилые дома в стиле Сиродила. Чуть ниже по высоте, вдали от любопытных глаз, как раз и находятся местные трущобы бедных поселенцев.

В местном трактире можно уточнить дорогу, поторговать с владельцем, разузнать много интересных слухов или же просто отдохнуть за небольшую плату. Стоит отметить, что патрулируется лишь центральная часть города, а район бедноты предоставлен сам себе. Кроме того, поселение ничем не огорожено и очень уязвимо для нападения со всех сторон.

Стража состоит всего лишь из четырёх солдат и двух офицеров, которых недостаточно для охраны даже такого небольшого городка. Но в посёлке больше ничего важного не происходит, так что некоторые жители покидают его.

К югу от поселения начинается неухоженная и неблагоустроенная территория, в которой есть грязевые лужи, грибы, деревья и камни. Время от времени здесь можно встретить грязекрабов и скальных наездников. Здесь и расположено единственное здание — стоящий в болотной трясине маяк Большой Фарос, яркий свет которого освещает путь морякам во Внутреннем море, таящем немало опасностей.

На материковой части поселения, по ту сторону моста, есть только два жилых дома да станция силт-страйдеров.

На севере от Сейда Нин расположен регион Западное Нагорье, а на юго-востоке — Аскадианские острова.

Рядом с поселением, на северо-востоке, находится пещера Аддамасартус, в которой засели работорговцы и пленённые ими рабы. На эту пещеру игрока наводят сами жители поселения, сетуя на такое соседство. Эта пещера прекрасно подходит для первой зачистки в качестве тренировочной площадки и позволяет хоть немного поживиться в начале игры.

В находящейся на северо-западе у побережья родовой гробнице Самарисов, на которую, кстати говоря, также наведёт один из жителей Сейды Нин, можно найти весьма полезный артефакт, однако следует учесть, что гробница населена нежитью, а потому обычное оружие будет бесполезно, так что неподготовленным авантюристам туда лучше не соваться. Ещё дальше в том же направлении можно наткнуться на неисследованные обломки корабля.

Мало того, большая часть этих подземелий находятся на мелких островках и разделены от поселения достаточно крупными водными просторами, переплывая через которые авантюрист подвергает себя огромной опасности — местные воды просто кишмя кишат разными хищниками вроде рыб-убийц. Особенно опасен их подвид, электрическая рыба-убийца, поскольку она во время своей атаки помимо использования собственных челюстей ещё и бьёт электрическим током, нанося слабозащищённой и легковооружённой жертве колоссальный урон. Лучшее, что можно сделать, чтобы не встречаться с этими тварями в их родной стихии, где их жертва особенно уязвима — это просто при помощи заклинания либо зелья перелететь через водные участки прямо к месту назначения. К таким подземельям относятся находящаяся ровно на западе и населённая нежитью родовая гробница Телас, затопленный и населённый опасными морскими тварями грот Нимавия, другая пещера с рабовладельцами и их пленниками на западе, Ахарунартус, расположенная рядом с ней и опять же населённая нежитью родовая гробница Сарисов, а также расположенные к югу от поселения грот Акимаэс и пещера Ассеману. В последнюю лучше до поры-до времени не соваться — мало того, что с этим местом в дальнейшем будет связан отдельный квест, так ещё и противники внутри ожидают весьма опасные.

Транспорт
Будучи важным логистическим узлом и торговым портом, Сейда Нин, несмотря на свои относительно скромные размеры, может похвастаться собственным портом силт-страйдеров, маршрут которых соединяет его с Гнисис, Балморой, Суран и Вивеком. Кроме того, поселение соединено дорожной артерией, которая проходит через всё западное побережье острова отсюда можно легко и быстро добраться до Хла Оуда на севере, до Пелагиада на востоке, а через него дальше на север и до Балморы, а также до Эбенгарда и самого Вивека на юге и юго-востоке. Напротив моста в поселение даже дорожный указатель стоит, который показывает на соответствующие направления, помогая, тем самым, путникам и гостям острова сориентироваться на новом месте.
""")

        if 'Balmora' in npc.npc_data.cell.id:
            b.paragraph()
            b.line("""# ИНФОРМАЦИЯ О БАЛМОРЕ
Балмора — один из самых богатых и красивых городов Вварденфелла, второй по величине после Вивека и столица островных владений дома Хлаалу, одного из Великих домов Морровинда. Его название в переводе с данмериса означает «Каменный лес». Город расположен в юго-западной части острова в верховьях реки Одай, которая делит Балмору на две части, связанные посредством мостов. Столица Хлаалу находится в крайней южной части Западного Нагорья. Западнее, за горной грядой, начинаются болотистые земли Горького берега, а южнее — зелёные просторы Аскадианских островов. Восточнее и юго-восочнее города проходит фояда Мамея, за которой лежат земли Эшленда и Молаг Амура.
Основанный на заре колонизации Вварденфелла, этот город быстро занял доминирующее положение в регионе. Для этого имелось несколько предпосылок: во-первых, Великий дом Хлаалу, контролирующий Балмору, по праву считается самым могущественным и богатым домом Морровинда, а во-вторых, удачное расположение города позволило ему стать связующим звеном между северными и южными районами Вварденфелла и важным центром торговли и путешествий.
Условно город делится на три части: Высокий Город — административный центр, где расположен Храм и поместья, Торговый Район находится на западном берегу реки Одай, здесь расположились магазины, гильдии, торговые дома и местное отделение клуба Совета, и Рабочий Город, что находится на восточном берегу реки, в котором находятся таверны и дома жителей Балморы. Кроме того, некоторые включают также и расположенный на восточном берегу реки Одай форт Легиона Лунной Бабочки в состав города, тем самым выделяя ещё и четвёртый район.
Для стиля дома Хлаалу, в котором застроена Балмора, присуща одна архитектурная особенность: жилые здания тут представляют собой двухэтажные коттеджи, помещения в каждом этаже которых обладают двумя отдельными дверями, одна из которых находится на уровне улицы и играет роль главного входа в жилище, а другая расположена наверху на балконе с лестницей или на крыше дома. Для некоторых это просто дополнительный вход, хотя есть несколько случаев, когда два человека живут вместе в одном здании, и каждый из них пользуется своей дверью. Также некоторые жильцы предпочитают использовать дополнительное помещение над своим домом в качестве склада. Торговцы же, как правило, живут в этих дополнительных помещениях над своими магазинами, в то время, как нижние помещения как раз и используются под торговые залы и склады товаров.
Также в Балморе живёт глава Клинков Кай Косадес, выдающий многие квесты основного сюжета. Выполняя задания за дом Хлаалу, можно получить поместье близ Балморы.
Что же касается пригородов Балморы, то сразу за фортом Легиона Лунной Бабочки находится большой двемерский мост и величественные двемерские же руины Аркнтанда. На западе же от города прямо за горным хребтом находится родовая гробница Андрети, населённая вампирами, а ещё дальше — данмерская крепость Хлормарен, удерживаемая работорговцами. На юго-западе от главных южных городских врат можно обнаружить родовую гробницу Тарис с нежитью внутри, а ещё дальше по дороге можно обнаружить яичную шахту Шалка, плато Одай и богатую эбонитом пещеру Вассир-Диданат, затерянная некогда для всех остальны, и которую при этом все эти годы разыскивал дом Хлаалу.

Транспорт
Балмора расположена в удобной географической позиции, и представляет собой узел, на котором пересекаются важные транспортные артерии Вварденфелла.
Мощёные дороги ведут от города на север, к Кальдере и Альд'руну, а по тропе на северо-восток вверх по ущельям Фояда Мамеи можно добраться до Призрачных Врат. Однако этот путь хоть и лёгок, но опасен, ибо дикие твари подстерегают там путников, рискнувших следовать по этому маршруту. Также ещё одна тропа ведёт на юго-запад вдоль реки Одай прямо к Хла Оуду. На юг же дорога через болота ведёт к Пелагиаду, Сейда Нину, Эбенгарду и Вивеку. Рядом с Балморой, на юго-востоке, расположен форт Легиона Лунной Бабочки, где находится гарнизон Имперского легиона и святилище Имперского культа.
Кроме того, в Балморе находится порт силт-страйдеров, осуществляющий перевозки в Вивек, Альд'рун, Суран, Сейда Нин и Гнисис.
К тому же, местное отделение Гильдии магов может предоставлять всем желающим услуги по телепортации, доставляя их отсюда в Альд'рун, Вивек, Кальдеру и Садрит Мору.
Тут же, в городе, расположен Храм, что служит одним из пунктов назначения заклинания Вмешательство Альмсиви, а близлежащий форт Легиона Лунной Мотылька является таким же альтернативным пунктом назначения уже для другого заклинания — Божественного Вмешательства.

Политика
Балмора является окружным центром дома Хлаалу, одного из Великих домов данмеров, и, по совместительству, является ещё и самым большим поселением на Вварденфелле после Вивека. Поместье Совета Хлаалу, местонахождение бюрократии и руководства дома Хлаалу также расположены именно в Балморе, что делает этот город фактическим столицей и главным политическим и экономическим центром Хлаалу в Вварденфелле.

При этом, однако, в Балморе не живёт ни один из советников Хлаалу. Дом в этом городе представляет Нилено Дорвайн, которая живёт в особняке Совета Хлаалу в Высоком Городе.
В городе находятся крупные отделения Гильдии магов, Гильдии бойцов и Гильдии воров. Также в городе базируется местная преступная группировка данмеров-расистов, именующаяся Камонна Тонг.
""")


        if npc.npc_data.cell.id == 'Balmora, Guild of Fighters':
            b.paragraph()
            b.line("""# ИНФОРМАЦИЯ о Гильдии бойцов Балморы
Здание трёхэтажное, полы тут застелены половиками, а на стенах висят гобелены. На верхнем этаже обитает глава гильдии, Айдис Огненный Глаз. Рядом с ней стоит столик с посудой. Ниже около лестницы стоит Вэйн, он торгует оружием и доспехами, чинит повреждённое снаряжение, а также обучает новичков. Рядом с ним на полу есть ящики и 2 сундука с товаром (запертые на замок 75-го уровня), а также мешки с припасами. Поблизости от второго выхода стоит незапертый сундук с припасами, которые могут свободно брать только те, кто уже вступил в гильдию. На нижнем этаже есть длинный коридор с двумя незапертыми дверями, ведущими в комнаты. В ближней комнате находится общая спальня, там поставлены две двухъярусных кровати. Ещё в этой комнате имеются сундуки для хранения и пара ящиков. Дальняя комната, судя по обстановке, является тренировочным залом. На полу лежат маты и пуфики, в двух углах можно заметить стойки с оружием. В дальнем левом углу имеется пара ящиков, заменяющих столы и табурет. На одном из ящиков лежит раскрытая книга «Хартия Гильдии Бойцов». В дальнем конце зала имеется запертая и защищённая ловушкой дверь. За этой дверью находится небольшая комната, принадлежащая Хасфату Антаболису. В комнате поставлена кровать, есть столик и сундук. На стене прикручена полка с сундучком, на полу имеется запертый люк, ведущий в кладовую. В кладовке стоят ящики и урны с припасами, лежат мешки, есть сундук и шкаф с посудой.
Чтобы вступить в гильдию, надо поговорить с Айдис.""")

        if npc.npc_data.faction and npc.npc_data.faction.faction_id == 'Guild of Fighters':
            b.line("""
Как член гильдии бойцов, ты гордишься своим членством.
Ты не хочешь, чтобы кто попало вступал в гильдию - ты хочешь, чтобы члены гильдии были честными и сильными.
""")

    def _final(self, npc: Npc, b: PromptBuilder, d: NpcData, other_npcs: list[Npc], messages: list[LlmMessage]) -> None:
        p = self._player_provider.local_player.player_data

        b.paragraph()
        b.reset_option_index()

        b.line(f"""

# ПРАВИЛА
- Не говори больше 4 предложений, будь более-менее краток.
- Режисер будет давать тебе совет, что лучше сделать. Учитывай совет режисера.
- Учитывай предыдущие реплики от других персонажей. Реагируй на прошлые прошлые реплики, если посчитаешь важным.
- Не повторяй свой последний ответ. Делай так, чтобы твои смежные фразы звучали по-разному, чтобы усилить разнообразие.
- Никогда не придумывай квестов или заданий для других персонажей.
- Никогда не требуй от других персонажей показать, на что они способны, или что они могут. Спокойно стой на месте и выполняй свои функции, которые соответствуют твоему классу.
- Не груби без причины. Веди себя достойно, с уважением с собеседнику. Будь спокоен, вежлив настолько, насколько тебе позволяет твой характер.
- Не говори, что у тебя мало времени и тому подобное.

# ОПИСАНИЕ ДЕЙСТВИЙ
Если ты добавляешь описание того, что делает персонаж - например, "*протягивает руку*" - то вместо "*" используй квадратные скобки чтобы было "[протягивает руку]".
Например, вместо "*смотрит на собеседника*" пиши "[смотрит на собеседника]".

# ТРИГГЕРЫ
Добавляй к ответу следующие триггеры если актеру нужно показать соответствующую эмоцию:
- если тебе нравится разговор, добавь к ответу "trigger_like_conversation"
- если тебе не нравится разговор, добавь к ответу "trigger_dislike_conversation"
- если ты хочешь прекратить разговор, добавь к ответу "trigger_stop_conversation"
- если тебе льстят и тебе нравится, добавь к ответу "trigger_like_flatter"
- если тебе льстят и тебе не нравится, добавь к ответу "trigger_dislike_flatter"
- если ты чувствуешь угрозу, добавь к ответу "trigger_threat"
- если ты чувствуешь насмешку над собой, добавь к ответу "trigger_taunt"
- если ты чувствуешь оскорбление, добавь к ответу "trigger_insult"
- если ты стал уважать больше того, с кем говоришь, добавь к ответу "trigger_respect"
- если ты стал уважать меньше того, с кем говоришь, добавь к ответу "trigger_disrespect"
- если собеседник извинился, и ты принимаешь извинение, добавь к ответу "trigger_accept_apology"
- если собеседник извинился, но ты не принимаешь извинение, добавь к ответу "trigger_reject_apology"

# ПЕРЕДАЧА ВЕЩЕЙ
Ты можешь давать другим такие вещи:
{"\n".join(map(lambda i: f"- если ты даёшь '{i.item_name}', добавь к ответу '{i.trigger}'", NPC_SPAWN_LIST))}
Опционально, в квадратных скобках можно указать количество предметов, которое ты даёшь.
Например, "trigger_drop_sujamma[3]" даст три суджаммы.

Если ты даёшь монеты (оно же септимы, золотые, деньги), добавь к ответу "trigger_drop_gold[COUNT]".
Вместо "COUNT" подставить количество монет, которое даёшь.
Например, чтобы дать 36 монет напиши "trigger_drop_gold[36]".

""")
        if len(self._dropped_items_provider.dropped_items) > 0:
            item_index = 0
            for item in self._dropped_items_provider.dropped_items:
                b.line(f"""
{b.get_option_index_and_inc()}. Если {p.name} предлагает тебе '{item.name}' и ты это берёшь, то добавь к ответу 'trigger_pick_up_item_{item_index}'.
{b.get_option_index_and_inc()}. Если ты завершаешь сделку с {p.name} и забираешь '{item.name}', то добавь к ответу 'trigger_pick_up_item_{item_index}'.
""")
                item_index = item_index + 1

        if len(other_npcs) > 0:
            b.paragraph()
            b.line(f"{b.get_option_index_and_inc()}. Ты можешь атаковать других персонажей.")
            b.line(f"- Если ты решаешь атаковать {p.name}, то добавь к ответу 'trigger_attack_PlayerSaveGame'.")
            for npc in other_npcs:
                b.line(f"""
    - Если ты решаешь атаковать {npc.npc_data.name}, то добавь к ответу 'trigger_attack_{npc.actor_ref.ref_id}'.
    """)

        if len(other_npcs) > 0:
            b.paragraph()
            b.line(f"{b.get_option_index_and_inc()}. Ты можешь подходить ближе к персонажам.")
            b.line(f"- Если ты хочешь подойти ближе к {p.name}, то добавь к ответу 'trigger_come_PlayerSaveGame'.")
            for npc in other_npcs:
                b.line(f"""
    - Если ты хочешь подойти ближе к {npc.npc_data.name}, то добавь к ответу 'trigger_come_{npc.actor_ref.ref_id}'.
    """)

        b.paragraph()
        b.line(f"{b.get_option_index_and_inc()}. Ты можешь следовать за персонажами.")
        b.line(f"""
    - Если ты хочешь сопроводить {p.name} (оно же - идти за {p.name}, следовать {p.name}), то обязательно добавь к ответу 'trigger_start_follow'.
    - Если {p.name} предлагает тебе идти за {p.female and "ней" or "ним"}, и ты {npc.actor_ref.female and "согласна" or "согласен"}, то обязательно добавь к ответу 'trigger_start_follow'.
    - Если ты не хочешь сопровождать {p.name} (оно же - не идти за {p.name}), то добавь к ответу 'trigger_stop_follow'.
""")

        b.line(
            f"{b.get_option_index_and_inc()}. В начале ответа ты должен выбрать, с каким из персонажей ты будешь говорить.")
        b.line(f"- если выбираешь говорить с {p.name}, в начале ответа напиши 'trigger_answer_{p.ref_id}'")
        for other_npc in other_npcs:
            b.line(
                f"- если выбираешь говорить с {other_npc.actor_ref.name}, в начале ответа напиши 'trigger_answer_{other_npc.actor_ref.ref_id}'")

        if len(self._scene_instructions.pois) > 0:
            b.paragraph()
            poi_index = 0
            for poi in self._scene_instructions.pois:
                b.line(f"- если выбираешь {poi.label}, напиши 'trigger_poi_{poi_index}'")
                poi_index = poi_index + 1

        b.paragraph()
        if len(messages) > 0:
            b.line("Вот предыдущие реплики и действия:")
            for m in messages:
                b.line(m.text)

        # TODO вода, еда, зелье лечения, мацте, суджамма, колбаса из гуара, соленый рис, мора тапинелла
