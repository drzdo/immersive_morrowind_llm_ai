import asyncio
from util.logger import Logger
import struct
from typing import Callable

from pydantic import BaseModel
from eventbus.backend.abstract import AbstractEventBusBackend
from eventbus.event import Event

logger = Logger(__name__)


class _ActiveClient:
    peer_name: str
    writer: asyncio.StreamWriter

    def __init__(self, peer_name: str, writer: asyncio.StreamWriter):
        self.peer_name = peer_name
        self.writer = writer

class MwseTcpEventBusBackend(AbstractEventBusBackend):
    class Config(BaseModel):
        port: int
        encoding: str

    def __init__(self, config: Config) -> None:
        super().__init__()

        self._config = config
        self._callback_for_event_from_game: Callable[[Event], None]

        self._active_clients: list[_ActiveClient] = []

    def is_connected_to_game(self) -> bool:
        return len(self._active_clients) > 0

    def start(self, callback: Callable[[Event], None]):
        self._callback_for_event_from_game = callback

        asyncio.get_event_loop().create_task(self._run_server())

    def publish_event_to_game(self, event: Event):
        for client in self._active_clients:
            try:
                self._publish_event_to_client(client, event)
            except Exception as error:
                logger.error(f"Falied to publish event to client {client.peer_name}: {error}")

    def _publish_event_to_client(self, client: _ActiveClient, event: Event):
        msg_json_str = event.model_dump_json()
        msg_bytes = msg_json_str.encode(encoding=self._config.encoding)

        header = struct.pack('>I', len(msg_bytes))
        client.writer.write(header)
        client.writer.write(msg_bytes)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peername = writer.get_extra_info("peername")
        address = peername[0]
        port = peername[1]

        client = _ActiveClient(peer_name=f"{address}:{port}", writer=writer)

        logger.info(f"Client #{client.peer_name} connected")
        self._active_clients.append(client)

        try:
            while True:
                msg_size_bytes = await reader.readexactly(4)
                msg_size: int = struct.unpack('>I', msg_size_bytes)[0]

                msg_bytes = await reader.readexactly(msg_size)
                msg = msg_bytes.decode(encoding=self._config.encoding)

                try:
                    event = Event.model_validate_json(msg, strict=True)
                    logger.debug(event)
                    self._callback_for_event_from_game(event)
                except Exception as error:
                    logger.error(f"Error happened during event deserialization: {msg} {error}")
        except Exception as error:
            logger.error(f"Error happened during serving the client: {error}")
        finally:
            self._active_clients.remove(client)
            writer.close()

    async def _run_server(self):
        Logger.set_ctx(f"mwse_tcp_server")

        server = await asyncio.start_server(self._handle_client, 'localhost', self._config.port)
        async with server:
            await server.serve_forever()
