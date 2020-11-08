import logging
import sys

from client.generic.forking import ForkingClient

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # TODO: should be in __init__()


class ForkingPlayerctlClient(ForkingClient):
    ua = f"{sys.platform}_forking_playerctl_{'.'.join(map(str, _version))}"

    def _define_commands(self):
        self._pause_cmd = "playerctl -p vlc pause"
        self._resume_cmd = "playerctl -p vlc play"
        self._seek_cmd = "playerctl -p vlc position {seek}"

        self._position_cmd = "playerctl -p vlc position"
        self._status_cmd = "playerctl -p vlc status"
        self._title_cmd = "playerctl -p vlc metadata xesam:url"
        self._length_cmd = "playerctl -p vlc metadata mpris:length"
