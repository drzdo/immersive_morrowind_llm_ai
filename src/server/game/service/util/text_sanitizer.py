from typing import Tuple

from eventbus.data.npc_data import NpcData
from game.i18n.i18n import I18n
from game.service.player_services.player_provider import PlayerProvider


class TextSanitizer:
    def __init__(self, i18n: I18n, player_provider: PlayerProvider) -> None:
        self._i18n = i18n
        self._player_provider = player_provider

        self._replacements: list[Tuple[str, str]] = [
            ("ё", "е"),
            ("Ё", "Е"),
            ("@", ""),
            ("#!", "!"),
            ("#.", "."),
            ("#?", "?"),
            ("⌂#", ""),
            ("()", ""),
            ("**", ""),
            ("%PCRank", self._i18n.str("коллега")),
        ]

    def sanitize(self, original: str, *, npc_data: NpcData | None = None) -> str:
        s = original
        for r in self._replacements:
            s = s.replace(r[0], r[1])

        player = self._player_provider.local_player
        s = s.replace('%PCName', player.player_data.name)
        s = s.replace('%PCRace', player.player_data.race.name)

        if npc_data:
            s = s.replace('%name', npc_data.name)
            s = s.replace('%faction', npc_data.faction.faction_name if npc_data.faction else "какая-то фракция")
            s = s.replace('%rank', f"{npc_data.faction.npc_rank}" if npc_data.faction else "какой-то ранг")
            s = s.replace('%nextrank', f"{npc_data.faction.npc_rank}" if npc_data.faction else "какой-то ранг")

        s = ' '.join(s.split())
        s = s.strip()

        return s.removeprefix(";")
