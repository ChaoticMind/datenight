import asyncio
from enum import Enum
from abc import ABC


class PlayerState(Enum):
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"


class SyncSuggestion(Enum):
    STATE = "state"
    SEEK = "seek"


class GenericPlayer(ABC):
    """_REACT_GRACE_PERIOD is used for:
    * Not emitting implicit request for pause/resume/seek if it's reacting
    on a request to pause/resume/seek by the server
    * As a desired side effect, setting show=False when reacting on a request
    to pause/resume/seek by the server (i.e. not polluting the subscribers log)
    """
    _REACT_GRACE_PERIOD = 0.1

    def __init__(self):
        self._just_reacted_task = None

    def _reset_just_reacted(self):
        self._just_reacted_task = None

    def _initiate_just_reacted(self):
        loop = asyncio.get_event_loop()
        if self._just_reacted_task:
            self._just_reacted_task.cancel()

        self._just_reacted_task = loop.call_later(
            self._REACT_GRACE_PERIOD, self._reset_just_reacted)
