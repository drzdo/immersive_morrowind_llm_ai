from typing import Literal, NamedTuple
from pydantic import BaseModel, Field
from pynput import keyboard
from eventbus.data.actor_ref import ActorRef
from game.data.npc import Npc
from util.logger import Logger

logger = Logger(__name__)

class SceneInstructions:
    class Config(BaseModel):
        file: str
        encoding: str = Field(default="utf-8")
        start_paused: bool = Field(default=False)

    class ManualInstruction(NamedTuple):
        actor_to_act: ActorRef
        reason: str
        pass_reason_to_npc: bool

    class PointOfInterest(NamedTuple):
        type: Literal['activate', 'travel']
        label: str
        pos: list[float]
        ref_id: str

    def __init__(self, config: Config | None) -> None:
        self._config = config
        self._hold_on = False

        self._listener_k = keyboard.Listener(
            on_press=self._handle_press,  # type: ignore
        )
        self._listener_k.start()

        self._manually_instructed_to_hold_on_instructions = False
        self.pois: list[SceneInstructions.PointOfInterest] = []

        if self._config:
            self._manually_instructed_to_hold_on_instructions = self._config.start_paused

    def _handle_press(self, key: keyboard.Key):
        if hasattr(key, 'vk') and key.__getattribute__('vk') == 110:  # NumPad.
            if self._manually_instructed_to_hold_on_instructions:
                self._manually_instructed_to_hold_on_instructions = False
                logger.info("Manual instructions hold on released")

    def get_next_manual_instruction_for_pick_npc(self, hearing_npcs: list[Npc]) -> ManualInstruction | None:
        if self._config is None:
            return None
        if self._manually_instructed_to_hold_on_instructions:
            return None

        file = open(self._config.file, 'r', encoding=self._config.encoding)
        all_lines = file.readlines()
        file.close()

        self.pois = []

        for line_index in range(0, len(all_lines)):
            line_raw = all_lines[line_index]
            line = line_raw.strip().lower()
            if line.startswith("#") or len(line) == 0:
                continue

            if line.startswith('poi '):
                components = line.replace('poi ', '').split(',')
                poi = SceneInstructions.PointOfInterest(
                    'activate' if components[0] == 'activate' else 'travel',
                    components[1],
                    [
                        float(components[2]),
                        float(components[3]),
                        float(components[4])
                    ],
                    components[5] if len(components) >= 6 else ''
                )
                self.pois.append(poi)
                continue

            all_lines[line_index] = f'# {line_raw}'
            file = open(self._config.file, 'w', encoding=self._config.encoding)
            file.writelines(all_lines)
            file.close()

            if line == 'hold':
                self._manually_instructed_to_hold_on_instructions = True
                logger.info(f"Found manual instruction to hold on")
                return None

            components = line.split(' ', 1)
            if len(components) == 0:
                logger.error(f"Invalid instruction row {line_index}: {components}")
                return None

            npc_ref_id = components[0]
            reason = components[1] if len(components) >= 2 else ""

            reason = reason.replace("всс", "в своем стиле")
            if reason.startswith('"') and reason.endswith('"'):
                reason = f"в своем стиле скажи: '{reason[1:-1]}'"

            pass_reason = len(reason) > 0

            for npc in hearing_npcs:
                if npc_ref_id.lower() in npc.actor_ref.ref_id.lower() or npc_ref_id.lower() in npc.actor_ref.name.lower():
                    logger.info(f"Found manual instruction for NPC {npc.actor_ref}: {components}")
                    return SceneInstructions.ManualInstruction(npc.actor_ref, reason, pass_reason)

            logger.error(f"Found manual instruction for not hearing NPC {npc_ref_id}: {components}")

        return None
