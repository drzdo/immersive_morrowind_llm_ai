from eventbus.event import Event
from eventbus.event_data.event_data_from_server import EventDataFromServer
from eventbus.event_producer import EventProducer
from game.data.time import GameTime
from game.i18n.i18n import I18n
from game.service.player_services.player_database import PlayerDatabase
from game.service.player_services.player_provider import PlayerProvider
from game.service.providers.env_provider import EnvProvider
from game.data.story_item import StoryItem, StoryItemDataAlias
from game.service.story_item.story_item_to_history import StoryItemToHistoryConverter
from game.service.util.format_date import format_date
from game.service.util.prompt_builder import PromptBuilder
from util.logger import Logger

logger = Logger(__name__)


class PlayerPersonalStoryService:
    def __init__(self, db: PlayerDatabase, player_provider: PlayerProvider, env_provider: EnvProvider, producer: EventProducer,
                 i18n: I18n) -> None:
        self._db = db
        self._player_provider = player_provider
        self._env_provider = env_provider
        self._producer = producer
        self._i18n = i18n

    def load_story_to_player(self):
        player = self._player_provider.local_player
        if new_story := self._db.load_personal_story(
            player.actor_ref.ref_id, self._env_provider.now()
        ):
            player.personal_story = new_story
            logger.info(f"Player story loaded with {len(new_story.items)} items")
        else:
            logger.info("Player story is empty")

    def add_items_to_personal_story(
        self,
        item_data_list: list[StoryItemDataAlias]
    ):
        if not item_data_list:
            return

        logger.debug(f"Add items to player's story: {item_data_list}")

        player = self._player_provider.local_player
        items: list[StoryItem] = []
        items.extend(
            StoryItem(
                item_id=player.personal_story.return_next_item_id_and_inc(),
                time=self._env_provider.now(),
                data=item_data,
            )
            for item_data in item_data_list
        )
        player.personal_story.items.extend(items)
        self._db.save_personal_story(player)

        self.publish_player_story()

    def publish_player_story(self):
        logger.debug("Publish player story to the game")

        self._producer.produce_event(Event(
            data=EventDataFromServer.UpdatePlayerBook(
                type='update_player_book',
                player_book_name=self._db.config.book_name,
                player_book_content=self._build_book_content()
            )
        ))

    def _build_book_content(self):
        b = PromptBuilder()

        now = self._env_provider.now().game_time
        b.line(
            f"(Сейчас {format_date(now.day, now.month, now.year)}, {self._i18n.format_time(now.hour)})")

        items = self._player_provider.local_player.personal_story.items[-self._db.config.max_shown_story_items:]

        # b.new_paragraph()

        last_time: GameTime | None = None

        for item in items:
            b.line()
            time = item.time.game_time
            b.paragraph()

            d = item.data

            if last_time != time:
                if last_time is None or last_time.day != time.day:
                    b.line(
                        f"{format_date(time.day, time.month, time.year)}, {self._i18n.format_time(time.hour)}")
                elif last_time.hour != time.hour:
                    b.line(f"{self._i18n.format_time(time.hour)}")

            b.line(
                StoryItemToHistoryConverter.convert_item_to_line(
                    'player_story', self._player_provider.local_player.actor_ref, d)
            )

            last_time = time

        text = b.__str__()
        text = text.replace("\n", "<br>")
        text = f"{text}<br>"

        return text
