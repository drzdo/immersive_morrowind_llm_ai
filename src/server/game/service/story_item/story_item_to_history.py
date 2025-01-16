from typing import Literal

from eventbus.data.actor_ref import ActorRef
from game.data.story_item import StoryItemDataAlias
from game.service.story_item.npc_story_item_helper import NpcStoryItemHelper
from util.logger import Logger

logger = Logger(__name__)


class StoryItemToHistoryConverter:
    @staticmethod
    def convert_item_to_line(pov: Literal['npc_story', 'player_story', 'pick_actor'],
                             actor_pov: ActorRef | None, d: StoryItemDataAlias, delta_sec: float | None = None) -> str:
        delta_str = ''
        if delta_sec is not None:
            if delta_sec < 600:
                delta_str = 'только что '  # morrowind time scale is big
            elif delta_sec < 3600:
                delta_str = f'{round(delta_sec / 60)} минут назад '
            elif delta_sec < 3600 * 24:
                delta_str = f'{round(delta_sec / 3600)} часов назад '
            else:
                delta_str = f'{round(delta_sec / (3600 * 24))} дней назад '

        initiator_actor = NpcStoryItemHelper.get_initiator(d)
        initiator = initiator_actor.name if initiator_actor else 'кто-то'
        if initiator_actor == actor_pov:
            initiator = "я"

        target_actor = NpcStoryItemHelper.get_target(d)

        target_nom = target_actor.name if target_actor else None
        target_gen = target_nom
        target_dat = target_nom
        target_tvo = target_nom
        target_acc = target_nom

        if target_actor == actor_pov:
            target_nom = "я"
            target_gen = "меня"
            target_dat = "мне"
            target_tvo = "мной"
            target_acc = "меня"

        initiator_female = initiator_actor and initiator_actor.female
        a = "а" if initiator_female else ""
        ss = "ась" if initiator_female else "ся"

        match d.type:
            case 'change_disposition':
                if d.value > 0:
                    return f"({delta_str}{initiator} улучшил{a} своё отношение к {target_dat} на +{d.value})"
                else:
                    return f"({delta_str}{initiator} ухудшил{a} своё отношение к {target_dat} на {d.value})"
            case 'npc_start_follow':
                return f"({delta_str}{initiator} решил{a} идти вместе с {target_tvo})"
            case 'npc_stop_follow':
                return f"({delta_str}{initiator} решил{a} больше не идти вместе с {target_tvo})"
            case 'npc_pick_up_item':
                return f"({delta_str}{initiator} взял{a} {d.item_name})"
            case 'npc_trigger_dialog_topic':
                return f"({delta_str}{initiator} рассказал{a} {target_dat} про {d.topic_name}) {d.topic_response}"
            case 'player_trigger_dialog_topic':
                return f"({delta_str}{initiator} попросил{a} рассказать {target_acc} про {d.trigger_topic}) {d.original_text}"
            case 'player_trigger_list_dialog_topics':
                return f"({delta_str}{initiator} попросил{a} рассказать {target_acc} про специальные темы) {d.original_text}"
            case 'npc_attack':
                return f"({delta_str}{initiator} решил{a} атаковать {target_acc})"
            case 'ashfall_eat_stew':
                return f"({delta_str}{initiator} купил{a} {d.stew_name} за {d.cost} монет у {target_gen}, и съел{a})"
            case 'npc_death':
                if d.killer:
                    return f"({delta_str}{initiator} убил{a} {target_acc})"
                else:
                    return f"({delta_str}{initiator} был{a} убит{a})"
            case 'say_processed':
                if d.target:
                    return f"({delta_str}{initiator} сказал{a} {target_dat}) {d.text}"
                else:
                    return f"({delta_str}{initiator} сказал{a} вслух) {d.text}"
            case 'say_raw':
                logger.error(f"say_raw should not be added to the story: npc={actor_pov} data={d}")
                return ''
            case 'barter_offer':
                selling = ", ".join(d.selling)
                buying = ", ".join(d.buying)
                v = abs(d.value)
                if d.success:
                    if d.value < 0:  # initiator was buying
                        if len(selling) > 0:
                            return f"{delta_str}{initiator} купил{a} у {target_gen} {buying}, при этом продав {selling} и доплатив {v} монет"
                        else:
                            return f"{delta_str}{initiator} купил{a} у {target_gen} {buying} в сумме за {v} монет"
                    elif d.value > 0:  # initiator was selling
                        if len(buying) > 0:
                            return f"{delta_str}{initiator} продал{a} {target_dat} {selling}, при этом купив {buying} и получив {v} монет сдачи"
                        else:
                            return f"{delta_str}{initiator} продал{a} {target_dat} {selling} в сумме за {v} монет"
                    else:
                        return f"{delta_str}{initiator} обменял{ss} с {target_dat}: {initiator} отдал{a} {selling}, при этом взяв у {target_gen} {buying}"
                else:
                    if d.value < 0:  # initiator was buying
                        if len(selling) > 0:
                            return f"{delta_str}{initiator} попытал{ss} купить у {target_gen} {buying}, при этом предлагая {selling} и {v} монет сверху - но {target_nom} отказался"
                        else:
                            return f"{delta_str}{initiator} попытал{ss} купить у {target_gen} {buying} в сумме за {v} монет - но {target_nom} отказался"
                    elif d.value > 0:  # initiator was selling
                        if len(buying) > 0:
                            return f"{delta_str}{initiator} попытал{ss} продать {target_dat} {selling}, при этом предлагая {buying} и {v} монет сдачи - но {target_nom} отказался"
                        else:
                            return f"{delta_str}{initiator} попытал{ss} продать {target_dat} {selling} в сумме за {v} монет - но {target_nom} отказался"
                    else:
                        return f"{delta_str}{initiator} попытал{ss} обменять с {target_dat}: {initiator} бы отдал{a} {selling}, при этом бы взяв у {target_gen} {buying} - но {target_nom} отказался"
            case 'actor_pick_reason':
                match pov:
                    case 'npc_story':
                        return ''
                    case 'pick_actor':
                        return f"(режисер сказал) {d.reason}"
                    case 'player_story':
                        return f"({d.reason})"
            case 'npc_drop_item':
                if d.count > 1:
                    return f"({delta_str}{initiator} положил{a} {d.count} {d.item_name})"
                else:
                    return f"({delta_str}{initiator} положил{a} {d.item_name})"
            case 'player_cell_changed':
                if d.cell.display_name:
                    return f"({delta_str}{initiator} {"зашла" if initiator_female else "зашел"} в {d.cell.display_name})"
                else:
                    return ""
            case 'npc_come':
                return f"({delta_str}{initiator} {"подошла" if initiator_female else "подошел"} к {target_dat})"
            case 'player_tells_to_shut_up':
                return f"({delta_str}{initiator} попросил{a} всех замолчать)"
            case 'player_tells_to_stop_combat':
                return f"({delta_str}{initiator} попросил{a} всех заткнуться и прекратить драться)"
            case 'player_trigger_sheogorath_level':
                match pov:
                    case 'npc_story':
                        return ''
                    case 'pick_actor':
                        return ''
                    case 'player_story':
                        match d.sheogorath_level:
                            case 'normal':
                                return f"({delta_str}{initiator} призвал спокойного Шеогората)"
                            case 'mad':
                                return f"({delta_str}{initiator} воззвал к безумию Шеогората)"
            case 'player_points_at_ref':
                return ""
                # if d.target_owner:
                #     if actor_pov and d.target_owner == actor_pov:
                #         return f"{delta_str}{initiator} {"указала пальцем" if initiator_female else "указал пальцем"} на лежащий неподалеку мой '{d.target_name}'"
                #     else:
                #         return f"{delta_str}{initiator} {"указала пальцем" if initiator_female else "указал пальцем"} на лежащий неподалеку '{d.target_name}' который принадлежит {d.target_owner.name}"
                # else:
                #     return f"{delta_str}{initiator} {"указала пальцем" if initiator_female else "указал пальцем"} на лежащий неподалеку '{d.target_name}', который по всей видимости никому не принадлежит"

#     buying:
    # - Дешевое восстановление здоровья
    # merchant:
    #   name: Шарн гра-Музгоб
    #   ref_id: sharn gra-muzgob00000000
    #   type: npc
    # offer: -15
    # selling: []
    # success: true
    # type: barter_offer
    # value: -15
