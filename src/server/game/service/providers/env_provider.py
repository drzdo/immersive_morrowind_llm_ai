import asyncio
from eventbus.data.env_data import EnvData
from eventbus.rpc import Rpc
from game.data.time import GameTime, Time
from util.logger import Logger


class EnvProvider:
    def __init__(self, env_data: EnvData, rpc: Rpc) -> None:
        self._env: EnvData = env_data
        self._rpc = rpc

        asyncio.get_event_loop().create_task(self._update_env_loop())

    def now(self) -> Time:
        game_time = GameTime(day=self._env.current_day, month=self._env.current_month,
                             year=self._env.current_year, hour=self._env.current_hour)
        return Time(game_time=game_time)

    @property
    def env(self):
        return self._env

    async def _update_env_loop(self):
        Logger.set_ctx(f"EnvProvider")

        while True:
            await asyncio.sleep(15.0)

            env_data = await self._rpc.get_env()
            self._env = env_data
