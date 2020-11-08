import logging
import sys
import os
import urllib.request
import asyncio

import gi

gi.require_version('Playerctl', '2.0')
from gi.repository import GLib, Playerctl  # noqa: E402

_version = (0, 0, 1)  # TODO: should be in __init__()

log = logging.getLogger(__name__)


class IntrospectiveVLCClient:
    """Uses GLib introspection library (see playerctl documentation)"""
    REPORT_PERIOD_S = 1
    ua = "{}_introspective_{}".format(
        sys.platform, '.'.join(map(str, _version)))

    def __init__(self, sock, offset=0):
        self._sock = sock

        self._state = "Paused"
        self._title = ""
        self._position = 0
        self._length = 0
        self.offset = offset

        self.__initialize_player()

        log.info("Initialized {} player".format(self.__class__.__name__))
        self.handle = asyncio.create_task(self._report_and_reschedule())
        # triggerring _report_and_reschedule() not strictly necessary since
        # on_stop/_on_play/_on_pause are called next, but just in case.

        initial_metadata = self._player.get_property("metadata")
        if initial_metadata:
            self._on_metadata(self._player, initial_metadata,
                              dontsend=True)  # set metadata

        if self._title:
            log.info("Player is running with {}".format(self._title))
            if self._player.get_property("status") == "Playing":
                self._on_play(self._player)  # set state etc
            elif self._player.get_property("status") == "Paused":
                self._on_pause(self._player)  # set state etc
            elif self._player.get_property("status") == "Stopped":
                self._on_stop(self._player)  # set state etc
            else:
                log.warning(f"Player in unknown state: "
                            f"{self._player.get_property('status')}")
        else:
            self._on_stop(self._player)  # set state etc

    def __initialize_player(self):
        log.info('initializing player')
        self._player = Playerctl.Player(player_name='vlc')
        self._player.connect('playback-status::playing', self._on_play)
        self._player.connect('playback-status::paused', self._on_pause)
        self._player.connect('playback-status::stopped', self._on_stop)
        self._player.connect('seeked', self._on_seek)
        self._player.connect('exit', self._on_exit)
        self._player.connect('metadata', self._on_metadata)

    # actions requested
    def pause(self):
        log.info("Received request to pause")
        try:
            self._player.pause()
        except GLib.GError:
            log.error("Can't play current file (if any)")

    def resume(self):
        log.info("Received request to resume")
        try:
            self._player.play()
        except GLib.GError:
            log.error("Can't resume current file (if any)")

    def seek(self, seek_dst):
        adjusted_seek = seek_dst + self.offset
        log.info("Received request to seek to {}".format(adjusted_seek))
        try:
            self._player.set_position(adjusted_seek * 1000000)
        except GLib.GError:
            log.error("Can't seek current file (if any)")
        except OverflowError:
            log.warning("seek destination too large, ignoring...")

    # events occurred
    def _on_metadata(self, player, e, dontsend=False):
        log.debug("New metadata: {}".format(e))
        # set title
        if 'xesam:artist' in e.keys() and 'xesam:title' in e.keys():  # music
            log.info('Now playing track: {artist} - {title}'.format(
                artist=e['xesam:artist'][0], title=e['xesam:title']))
            title = player.get_title()
        elif 'xesam:title' in e.keys():  # vid with metadata
            title = player.get_title()
            log.info('Now playing file: {}'.format(title))
        elif 'xesam:url' in e.keys():  # arbitrary file
            fname = os.path.basename(e['xesam:url'])
            title = urllib.request.unquote(fname)
            log.info('Now playing file: {}'.format(title))
        else:
            if player.get_property("status") == "Stopped":
                title = ""
            # self._on_stop(player)
            else:
                title = "?"
                log.info('Now playing unknown file')

        # get length
        if 'mpris:length' in e.keys():
            length = int(e['mpris:length']) // 1000000
        else:
            length = 0

        if (title != self._title) or (length and (length != self._length)):
            self._title = title
            if length:
                self._length = length
            if not dontsend:
                asyncio.create_task(
                    # too spammy on file change if show is True
                    self._report_and_reschedule(show=False)
                )

    def _on_play(self, player, status=None):
        log.info("Playing: {}".format(self._title))
        self._state = "Playing"
        asyncio.create_task(self._report_and_reschedule(show=True))

    def _on_pause(self, player, status=None):
        log.info("Paused: {}".format(self._title))
        self._state = "Paused"
        asyncio.create_task(self._report_and_reschedule(show=True))

    def _on_stop(self, player, status=None):
        log.info("Player is stopped...")
        self._state = "Stopped"
        self._title = ""
        self._length = 0
        asyncio.create_task(self._report_and_reschedule(show=True))

    def _on_exit(self, player):
        log.info('Player exited!')
        return self._on_stop(player)

    def _on_seek(self, player, seek):
        log.info(f'Seeked to {seek}')
        asyncio.create_task(self._report_and_reschedule(show=False))

    # periodic report
    async def _report_and_reschedule(self, show=False):
        """:param show: A recommendation whether to explicitly log on the
        subscriber side

        """
        self.handle.cancel()

        self._position = self._player.get_property("position") // 1000000
        if self._length and self._position:
            adjusted_position = self._position - self.offset
        else:
            adjusted_position = self._position
        log.debug("Reporting state")
        await self._sock.emit("update state", {
            "title": self._title,
            "status": self._state,
            "position": "{}/{}".format(adjusted_position, self._length),
            "show": show})

        self.handle.cancel()
        self.handle = asyncio.create_task(asyncio.sleep(self.REPORT_PERIOD_S))
        await self.handle
        asyncio.create_task(self._report_and_reschedule())
