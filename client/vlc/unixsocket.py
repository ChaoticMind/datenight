import logging
import sys
import os
import urllib.request
import asyncio
from functools import partial
from typing import Optional

from client import version
from client.generic import PlayerState, SyncSuggestion, GenericPlayer

log = logging.getLogger(__name__)


class UnixSocketClient(GenericPlayer):
    """Currently specific to vlc, but can be generalized similar to
    ForkingClient """
    REPORT_PERIOD = 1
    ua = f"{sys.platform}_unixsocket_{'.'.join(map(str, version))}"

    class UnixProtocol(asyncio.Protocol):
        def __init__(self, client: 'UnixSocketClient', *args, **kwargs):
            self._client = client

            self._pause_strings = ["status change: ( pause state: 3 ): Pause"]
            self._play_strings = ["status change: ( play state: 2 ): Play",
                                  "status change: ( play state: 3 )"]
            # think I saw this once as a play_string, but can't reproduce:
            # "status change: ( pause state: 4 )"
            self._stop_strings = ["status change: ( play state: 4 ): End",
                                  "status change: ( stop state: 0 )",
                                  "status change: ( pause state: 4 ): End"]

            self._state: PlayerState = PlayerState.PAUSED
            self._title = ""
            self._position = 0
            self._length = 0

            super().__init__(*args, **kwargs)

        def connection_made(self, transport):
            self._transport = transport
            log.debug("Connection to unixsocket established")

        def send_data(self, data):
            log.debug(f"Writing to the unix socket: {data.encode()}")
            self._transport.write(data.encode())

        @staticmethod
        def _droppable_strings(x):
            if x.startswith('status change:'):
                # used when state is updated
                return True
            elif x.startswith('seek: returned '):
                # used when seeking and immediately updating/probing
                return True
            elif x.startswith('pause: returned'):
                # used when seeking from a paused state
                return True
            else:
                return False

        def data_received(self, data):
            decoded = data.decode('utf-8').strip()
            log.debug(f'Data received on the unix socket: {decoded}')

            lines = decoded.split('\r\n')
            one_shots = [line for line in lines
                         if line.startswith('status change:')]
            lines = [line for line in lines if
                     not self._droppable_strings(line)]  # filter
            for x in one_shots:
                if x.startswith("status change: ( new input:"):
                    # VLC possible bug: doesn't emit new input or "play" to the
                    # socket unless the socket is written to by something else
                    # first? - strange.
                    skip = len("status change: ( new input:")
                    fname = os.path.basename(x[skip:])
                    self._title = urllib.request.unquote(fname)
                    asyncio.create_task(self.emit_to_sock(show=True))
                elif x in self._pause_strings:
                    suggest_sync = (None if self._client._just_reacted_task
                                    else SyncSuggestion.STATE)
                    log.info(f"Reporting pause state with {suggest_sync}")
                    self._state = PlayerState.PAUSED
                    asyncio.create_task(self.emit_to_sock(
                        show=True if suggest_sync else False,
                        suggest_sync=suggest_sync,
                    ))
                elif x in self._play_strings:
                    suggest_sync = (None if self._client._just_reacted_task
                                    else SyncSuggestion.STATE)
                    log.info(f"Reporting playing state with {suggest_sync=}")
                    self._state = PlayerState.PLAYING
                    asyncio.create_task(self.emit_to_sock(
                        show=True if suggest_sync else False,
                        suggest_sync=suggest_sync,
                    ))
                elif x in self._stop_strings:
                    self._state = PlayerState.STOPPED
                    self._position = 0
                    self._length = 0
                    self._title = ""
                    log.info("Reporting stopped state")
                    asyncio.create_task(self.emit_to_sock(show=True))
                elif x.startswith("status change: ( time: "):
                    try:
                        skip = len("status change: ( time: ")
                        reported_position = int(x[skip:-3])
                    except ValueError:
                        pass
                    else:
                        suggest_sync = (None if self._client._just_reacted_task
                                        else SyncSuggestion.SEEK)
                        self._position = reported_position
                        asyncio.create_task(self.emit_to_sock(
                            show=True if suggest_sync else False,
                            suggest_sync=suggest_sync,
                        ))
                else:  # other line starting with "status change" - unsupported
                    # e.g. volume changed
                    pass

            log.debug(f"received {len(lines)} lines")
            if len(lines) == 3:
                position, title, length = lines
                try:
                    position = int(position)
                    length = int(length)
                except ValueError:
                    return
                else:
                    if length != self._length or title != self._title:
                        self._length = length
                        self._title = title
                        asyncio.create_task(self.emit_to_sock(show=True))
                    elif position != self._position:
                        self._position = position
                        asyncio.create_task(self.emit_to_sock(show=False))

        async def emit_to_sock(
                self, *, show, suggest_sync: Optional[SyncSuggestion] = None):
            # could reset the periodic probe here, but it's not really required
            # introspective client behavior is to reset it atm
            log.debug(f"Reporting state with {suggest_sync=}")
            if self._length:
                adjusted_position = self._position - self._client.offset
            else:
                adjusted_position = self._position
            await self._client.websock.emit("update state", {
                "title": self._title,
                "status": self._state.value,
                "position": adjusted_position,
                "length": self._length,
                "show": show,
                "suggest_sync": suggest_sync.value if suggest_sync else None,
            })

        def connection_lost(self, e):
            log.debug(
                'The unix socket is now closed, cancelling periodic probe')
            if self._client.prober:
                self._client.prober.cancel()
            # Somehow those are not the same thing
            # maybe helpful: https://github.com/xxleyi/learning_list/issues/120
            # create_task raises an exception if I open and close VLC quickly.
            # asyncio.create_task(self._client.open_unixsock())
            asyncio.ensure_future(self._client.open_unixsock())

    def __init__(self, websock, offset=0):
        super().__init__()
        # self.reader = None
        # self.writer = None
        self.protocol = None
        self.websock = websock
        self.offset = offset
        self.prober = None

        asyncio.ensure_future(self.open_unixsock())

    async def open_unixsock(self):
        loop = asyncio.get_event_loop()
        expected_path = "/tmp/vlc.sock"
        try:
            ProtocolWithParam = partial(UnixSocketClient.UnixProtocol, self)
            transport, self.protocol = await loop.create_unix_connection(
                ProtocolWithParam, path=expected_path)
        # reader, writer = await asyncio.open_unix_connection(expected_path)
        # self.reader, self.writer = reader, writer
        except FileNotFoundError:
            log.critical(
                f'no unix socket found at {expected_path} - is vlc open?')
            loop = asyncio.get_event_loop()
            delayed_ensure_future = partial(asyncio.ensure_future,
                                            self.open_unixsock())
            loop.call_later(self.REPORT_PERIOD, delayed_ensure_future)
        else:
            loop = asyncio.get_event_loop()
            self.prober = loop.call_soon(self._periodic_probe)

    # actions requested
    def pause(self):
        log.info("Received request to pause")
        log.info(f"Current state is: {self.protocol._state.value}")
        if self.protocol._state == PlayerState.PLAYING:
            self.protocol._state = PlayerState.PAUSED
            self.protocol.send_data("pause\n")
            self._initiate_just_reacted()

    def resume(self):
        log.info("Received request to resume")
        log.info(f"Current state is: {self.protocol._state.value}")
        if self.protocol._state == PlayerState.PAUSED:
            self.protocol._state = PlayerState.PLAYING
            self.protocol.send_data("pause\n")  # means "resume"
            self._initiate_just_reacted()
        elif self.protocol._state == PlayerState.STOPPED:
            # 'play' only means start for the vlc rc client
            self.protocol._state = PlayerState.PLAYING
            self.protocol.send_data("play\n")
            self._initiate_just_reacted()

    def seek(self, seek_dst):
        adjusted_seek = seek_dst + self.offset
        log.info(f"Received request to seek to {adjusted_seek}")
        self.protocol._position = adjusted_seek
        if self.protocol._state == PlayerState.PAUSED:
            self.protocol.send_data("pause\n")  # resume
            self.protocol.send_data(f"seek {adjusted_seek}\n")
            self.protocol.send_data("pause\n")  # pause
            self._initiate_just_reacted()
        else:
            self.protocol.send_data(f"seek {adjusted_seek}\n")
            self._initiate_just_reacted()
            self._periodic_probe()

    def _periodic_probe(self):
        self.prober.cancel()
        log.debug("Probing...")
        self.protocol.send_data("get_time\n")
        self.protocol.send_data("get_title\n")
        self.protocol.send_data("get_length\n")

        loop = asyncio.get_event_loop()
        self.prober = loop.call_later(self.REPORT_PERIOD,
                                      self._periodic_probe)
