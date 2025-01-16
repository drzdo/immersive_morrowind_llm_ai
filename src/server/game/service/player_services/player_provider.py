import asyncio
from eventbus.rpc import Rpc
from game.data.player import Player


class PlayerProvider:
    def __init__(self, rpc: Rpc, player: Player):
        self._rpc = rpc
        self._local_player = player

        asyncio.get_event_loop().create_task(self._query_player())
        asyncio.get_event_loop().create_task(self._query_player_fast())

    @property
    def local_player(self):
        return self._local_player

    async def _query_player(self):
        while True:
            await asyncio.sleep(30)

            player_data = await self._rpc.get_local_player()
            self._local_player.player_data = player_data

    async def _query_player_fast(self):
        while True:
            await asyncio.sleep(5)

            player_data_fast = await self._rpc.get_local_player_fast()

            self._local_player.player_data.cell = player_data_fast.cell
            self._local_player.player_data.health_normalized = player_data_fast.health_normalized
            self._local_player.player_data.position = player_data_fast.position
            self._local_player.player_data.gold = player_data_fast.gold
            self._local_player.player_data.in_dialog = player_data_fast.in_dialog
            self._local_player.player_data.weapon_drawn = player_data_fast.weapon_drawn
            self._local_player.player_data.weapon = player_data_fast.weapon
