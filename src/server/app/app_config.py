from typing import Literal
from pydantic import BaseModel
import yaml

from database.database import Database
from game.service.npc_services.npc_database import NpcDatabase
from eventbus.backend.mwse_tcp import MwseTcpEventBusBackend
from eventbus.bus import EventBus
from eventbus.rpc import Rpc
from game.service.npc_services.npc_llm_pick_actor_service import NpcLlmPickActorService
from game.service.npc_services.npc_speaker_service import NpcSpeakerService
from game.service.player_services.player_database import PlayerDatabase
from game.service.scene.scene_instructions import SceneInstructions
from llm.system import LlmSystem
from stt.system import SttSystem
from tts.file_list_rotation import FileListRotation
from tts.system import TtsSystem
from util.logger import Logger

class AppConfig(BaseModel):
    morrowind_data_files_dir: str
    language: Literal['ru']
    log: Logger.Config
    speech_to_text: SttSystem.Config
    text_to_speech: TtsSystem.Config
    llm: LlmSystem.Config
    event_bus: EventBus.Config
    rpc: Rpc.Config
    database: Database.Config
    player_database: PlayerDatabase.Config
    npc_database: NpcDatabase.Config
    npc_director: NpcLlmPickActorService.Config
    npc_speaker: NpcSpeakerService.Config
    scene_instructions: SceneInstructions.Config | None

    @staticmethod
    def load_from_file(path: str):
        with open(path, 'r', encoding='utf-8') as f:
            d = yaml.full_load(f)
            return AppConfig.model_validate(d, strict=True)

    def save_to_file(self, path: str):
        d = self.model_dump(mode='json')
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(d, f, allow_unicode=True)

    @staticmethod
    def get_default():
        return AppConfig(
            morrowind_data_files_dir="specify",
            language='ru',
            log=Logger.Config(
                log_to_console=True,
                log_to_console_level='info',
                log_to_file=True,
                log_to_file_level='info'
            ),
            event_bus=EventBus.Config(
                consumers=10,
                producers=10,
                system=EventBus.Config.MwseTcp(
                    type='mwse_tcp',
                    mwse_tcp=MwseTcpEventBusBackend.Config(
                        port=18080,
                        encoding='cp1251'
                    )
                )
            ),
            rpc=Rpc.Config(
                max_wait_time_sec=5
            ),
            speech_to_text=SttSystem.Config(
                system=SttSystem.Config.Dummy(type='dummy'),
                delayed_stop_sec=0.5
            ),
            llm=LlmSystem.Config(
                system=LlmSystem.Config.Dummy(type='dummy')
            ),
            text_to_speech=TtsSystem.Config(
                system=TtsSystem.Config.Dummy(
                    type='dummy'
                ),
                output=FileListRotation.Config(
                    max_files_count=15,
                    file_name_format="tts_{}.mp3"
                )
            ),
            database=Database.Config(
                directory="specify"
            ),
            player_database=PlayerDatabase.Config(
                max_stored_story_items=200,
                book_name="Книга Путей",
                max_shown_story_items=40
            ),
            npc_database=NpcDatabase.Config(
                max_stored_story_items=200,
                max_used_in_llm_story_items=25
            ),
            npc_director=NpcLlmPickActorService.Config(
                npc_max_phrases_after_player_hard_limit=3,
                strategy_random=NpcLlmPickActorService.Config.StrategyRandom(
                    npc_phrases_after_player_min=2,
                    npc_phrases_after_player_max=6,
                    npc_phrases_after_player_min_proba=0.5
                ),
                random_comment_delay_sec=60,
                random_comment_proba=0.1
            ),
            npc_speaker=NpcSpeakerService.Config(),
            scene_instructions=None
        )
