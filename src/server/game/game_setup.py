import asyncio

from app.app_config import AppConfig
from game.data.story import Story
from game.service.npc_services.npc_intention_analyzer import NpcIntentionAnalyzer
from game.service.npc_services.npc_llm_pick_actor_service import NpcLlmPickActorService
from game.service.npc_services.npc_llm_system_instructions_builder import NpcLlmSystemInstructionsBuilder
from game.service.npc_services.npc_speaker_service import NpcSpeakerService
from game.service.player_services.player_database import PlayerDatabase
from game.service.player_services.player_personal_story_service import PlayerPersonalStoryService
from game.service.providers.cell_name_provider import CellNameProvider
from game.service.providers.dropped_items_provider import DroppedItemsProvider
from game.service.scene.scene_instructions import SceneInstructions
from game.service.util.text_sanitizer import TextSanitizer
from util.logger import Logger
from database.database import Database
from game.service.npc_services.npc_database import NpcDatabase
from eventbus.bus import EventBus
from eventbus.data.actor_ref import ActorRef
from eventbus.rpc import Rpc
from game.data.player import Player
from game.game_master import GameMaster
from game.i18n.i18n import I18n
from game.service.providers.dialog_provider import DialogProvider
from game.service.providers.env_provider import EnvProvider
from game.service.event_producers.event_producer_from_story import EventProducerFromStory
from game.service.player_services.player_intention_analyzer import PlayerIntentionAnalyzer
from game.service.npc_services.npc_behavior_service import NpcBehaviorService
from game.service.npc_services.npc_llm_response_producer import NpcLlmResponseProducer
from game.service.npc_services.npc_personal_story_service import NpcPersonalStoryService
from game.service.npc_services.npc_service import NpcService
from game.service.player_services.player_provider import PlayerProvider
from llm.system import LlmSystem
from stt.system import SttSystem
from tts.system import TtsSystem
from util.colored_lines import SUCCESS, WAITING

logger = Logger(__name__)


class GameSetup:
    @staticmethod
    async def setup_game_master(
        config: AppConfig,
        event_bus: EventBus,
        rpc: Rpc,
        stt: SttSystem,
        llm: LlmSystem,
        tts: TtsSystem,
        i18n: I18n
    ) -> GameMaster:
        #
        logger.info(f"{WAITING} Waiting for the Morrowind to connect to the server...")
        while not event_bus.is_connected_to_game():
            await asyncio.sleep(0.2)
        logger.info(f"{SUCCESS} Morrowind is connected")

        #
        logger.info(f"{WAITING} Requesting local player for the first time...")
        player_data = await rpc.get_local_player()
        player = Player(
            actor_ref=ActorRef(
                name=player_data.name,
                ref_id=player_data.ref_id,
                type='player',
                female=player_data.female
            ),
            player_data=player_data,
            personal_story=Story()
        )
        player_provider = PlayerProvider(rpc, player)
        logger.info(f"{SUCCESS} Got player data for '{player_data.name}'")

        database = Database(config.database, player.actor_ref.name)

        #
        logger.info(f"{WAITING} Requesting env for the first time...")
        env_data = await rpc.get_env()
        env_provider = EnvProvider(env_data, rpc)
        logger.info(f"{SUCCESS} Got env data")

        #
        player_db = PlayerDatabase(config.player_database, database)
        player_story_service = PlayerPersonalStoryService(player_db, player_provider, env_provider, event_bus, i18n)
        player_story_service.load_story_to_player()

        #
        text_sanitizer = TextSanitizer(i18n, player_provider)
        dropped_items_provider = DroppedItemsProvider(event_bus, rpc)
        dialog_provider = DialogProvider(event_bus)
        cell_name_provider = CellNameProvider(config.morrowind_data_files_dir, i18n)

        npc_database = NpcDatabase(config.npc_database, database)

        scene_instructions = SceneInstructions(config.scene_instructions)
        system_instructions_builder = NpcLlmSystemInstructionsBuilder(
            player_provider, env_provider, dropped_items_provider,
            cell_name_provider, i18n, scene_instructions)
        npc_llm_response_producer = NpcLlmResponseProducer(llm, env_provider, system_instructions_builder, i18n)
        pick_actor_service = NpcLlmPickActorService(config.npc_director, llm, env_provider, i18n, text_sanitizer,
                                                    scene_instructions)

        npc_behavior_service = NpcBehaviorService(
            config.npc_database.max_used_in_llm_story_items, env_provider, pick_actor_service, npc_llm_response_producer,
            dialog_provider)
        npc_service = NpcService(event_bus, rpc, npc_database, env_provider, llm.create_session())
        npc_speaker_service = NpcSpeakerService(config.npc_speaker, event_bus,
                                                event_bus, player_provider, tts, npc_service)
        npc_personal_story_service = NpcPersonalStoryService(npc_database, env_provider, event_bus)

        player_intention_analyzer = PlayerIntentionAnalyzer(llm)
        npc_intention_analyzer = NpcIntentionAnalyzer(
            player_provider, npc_service, text_sanitizer, dropped_items_provider,
            scene_instructions)

        event_producer_from_story = EventProducerFromStory(event_bus, player_provider, npc_service, i18n)

        #
        game_master = GameMaster(
            config, event_bus, event_bus,
            player_provider, player_story_service,
            dialog_provider, env_provider,
            npc_service, npc_behavior_service, npc_speaker_service, npc_personal_story_service, event_producer_from_story,
            player_intention_analyzer, npc_intention_analyzer, text_sanitizer, i18n, cell_name_provider)
        return game_master
