from util.logger import Logger
from eventbus.data.actor_ref import ActorRef
from game.data.story_item import StoryItemDataAlias

logger = Logger(__name__)


class NpcStoryItemHelper:
    @staticmethod
    def get_initiator(d: StoryItemDataAlias) -> ActorRef | None:
        match d.type:
            case 'say_raw':
                return d.speaker
            case 'say_processed':
                return d.speaker
            case 'change_disposition':
                return d.initiator
            case 'npc_start_follow':
                return d.initiator
            case 'npc_stop_follow':
                return d.initiator
            case 'npc_trigger_dialog_topic':
                return d.speaker
            case 'player_trigger_dialog_topic':
                return d.speaker
            case 'player_trigger_list_dialog_topics':
                return d.speaker
            case 'npc_attack':
                return d.initiator
            case 'npc_death':
                return d.killer
            case 'npc_pick_up_item':
                return d.initiator
            case 'ashfall_eat_stew':
                pass
            case 'barter_offer':
                return d.buyer
            case 'actor_pick_reason':
                return None
            case 'npc_drop_item':
                return d.initiator
            case 'player_cell_changed':
                return d.initiator
            case 'npc_come':
                return d.initiator
            case 'player_tells_to_shut_up':
                return d.speaker
            case 'player_tells_to_stop_combat':
                return d.speaker
            case 'player_trigger_sheogorath_level':
                return d.speaker
            case 'player_points_at_ref':
                return d.speaker

        return None

    @staticmethod
    def is_actor_is_initiator(ref: ActorRef, item_data: StoryItemDataAlias) -> bool:
        return NpcStoryItemHelper.get_initiator(item_data) == ref

    @staticmethod
    def get_target(d: StoryItemDataAlias) -> ActorRef | None:
        match d.type:
            case 'say_raw':
                return d.target
            case 'say_processed':
                return d.target
            case 'change_disposition':
                return d.target
            case 'npc_start_follow':
                return d.target
            case 'npc_stop_follow':
                return d.target
            case 'npc_trigger_dialog_topic':
                return d.target
            case 'player_trigger_dialog_topic':
                return d.target
            case 'player_trigger_list_dialog_topics':
                return d.target
            case 'npc_attack':
                return d.victim
            case 'npc_death':
                pass
            case 'npc_pick_up_item':
                return d.initiator
            case 'ashfall_eat_stew':
                pass
            case 'barter_offer':
                return d.merchant
            case 'actor_pick_reason':
                pass
            case 'npc_drop_item':
                pass
            case 'player_cell_changed':
                pass
            case 'npc_come':
                return d.target
            case 'player_tells_to_shut_up':
                pass
            case 'player_tells_to_stop_combat':
                pass
            case 'player_trigger_sheogorath_level':
                pass
            case 'player_points_at_ref':
                pass

        return None

    @staticmethod
    def is_actor_is_target(ref: ActorRef, item_data: StoryItemDataAlias) -> bool:
        return NpcStoryItemHelper.get_target(item_data) == ref
