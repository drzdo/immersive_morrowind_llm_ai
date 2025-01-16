import argparse
import asyncio
from llm.llm_logger import LlmLogger
from llm.message import LlmMessage
from util.logger import Logger
import time

from app.app_config import AppConfig
from eventbus.bus import EventBus
from eventbus.rpc import Rpc
from game.game_setup import GameSetup
from game.i18n.i18n import I18n
from llm.system import LlmSystem
from stt.system import SttSystem
from tts.system import TtsSystem
from util.colored_lines import SUCCESS, WAITING


logger = Logger(__name__)


class App:
    def run(self):
        asyncio.run(self._run())

    def _parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--config', type=str,
            help='path to config.yml file')
        parser.add_argument(
            '--write-default-config', required=False, type=str,
            help='write default config to the specified file path and exit')
        parser.add_argument(
            '--llm-probe', required=False, type=str,
            help='Take yml LLM log file and send it to the model')
        parser.add_argument(
            '--llm-probe-why', required=False, type=str,
            help='Ask LLM question about the history')
        args = parser.parse_args()
        return args

    async def _run(self):
        Logger.set_ctx("main")
        args = self._parse_args()

        if args.write_default_config:
            AppConfig.get_default().save_to_file(args.write_default_config)
            print(f"Default config saved to {args.write_default_config}")
        elif args.llm_probe:
            await self._run_llm_probe(args)
        else:
            await self._run_server(args)

    async def _run_llm_probe(self, args: argparse.Namespace):
        if args.config is None:
            print("Specify config with '--config <path to config.yml>")
            exit(1)

        config = AppConfig.load_from_file(args.config)
        Logger.setup_logs(config.log)

        llm = LlmSystem(config.llm)
        llm_session = llm.create_session()

        parsed_log = LlmLogger.parse(args.llm_probe)

        if args.llm_probe_why:
            parsed_log.messages.extend([
                LlmMessage(role='user', text=parsed_log.user_text),
                LlmMessage(role='model', text=parsed_log.model_text)
            ])
            llm_session.reset(
                system_instructions=parsed_log.system_instructions,
                messages=parsed_log.messages
            )
            model_message_new = await llm_session.send_message(user_text=args.llm_probe_why)
            logger.info(f"Model response:\n{model_message_new}")
        else:
            llm_session.reset(
                system_instructions=parsed_log.system_instructions,
                messages=parsed_log.messages
            )
            model_message_new = await llm_session.send_message(user_text=parsed_log.user_text)

            logger.info(f"Model response (old):\n{parsed_log.model_text}")
            logger.info(f"Model response (new):\n{model_message_new}")

    async def _run_server(self, args: argparse.Namespace):
        if args.config is None:
            print("Specify config with '--config <path to config.yml>")
            exit(1)

        config = AppConfig.load_from_file(args.config)
        Logger.setup_logs(config.log)

        logger.debug("Debug logs are enabled")

        t0 = time.time()
        logger.info(f"{WAITING} Initializing components...")

        event_bus = EventBus(config.event_bus)
        rpc = Rpc(config.rpc, event_bus)

        stt = SttSystem(config.speech_to_text, event_bus)
        llm = LlmSystem(config.llm)
        tts = TtsSystem(config.morrowind_data_files_dir, config.text_to_speech)
        i18n = I18n()

        logger.info(f"{SUCCESS} Initialization completed in {time.time() - t0} sec")

        t0 = time.time()
        logger.info(f"{WAITING} Preparing the game master...")
        event_bus.start()

        try:
            gm = await GameSetup.setup_game_master(config, event_bus, rpc, stt, llm, tts, i18n)
            gm.start()

            logger.info(f"{SUCCESS} Game master started in {time.time() - t0} sec")
            logger.info(f"Happy playing, game master is ready")

            while True:
                await asyncio.sleep(1.0 / 10.0)
        except asyncio.CancelledError or KeyboardInterrupt:
            logger.info("Ctrl-C-ed")
            pass
        except:
            raise
        finally:
            logger.info("Bye")
