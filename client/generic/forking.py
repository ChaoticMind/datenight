import logging
import sys
import os
import urllib.request
import asyncio
import time
from functools import partial
from typing import Optional

from client.generic import PlayerState, SyncSuggestion

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # TODO: should be in __init__()


class ForkingClient:
    """Client which forks another process to get and set properties

    Don't use this class directly, use one of its implementations instead
    Subclasses should overload the user agent (self.ua)
    and self._define_commands()

    """
    POLL_PERIOD_S = 0.9
    ua = f"{sys.platform}_forking_{'.'.join(map(str, _version))}"

    def __init__(self, sock, offset=0):
        self._sock = sock
        self._define_commands()

        self._state: PlayerState = PlayerState.PAUSED
        self._title = ""
        self._position = 0
        self._length = 0
        self.offset = offset

        log.info(f"Initialized {self.__class__.__name__} player")
        asyncio.create_task(self._periodic_report_metadata())

    def _define_commands(self):
        """Subclasses should implement the following variables
        self._pause_cmd, self._resume_cmd, self._seek_cmd
        self._position_cmd, self._status_cmd, self._title_cmd, self._length_cmd

        """
        raise NotImplementedError("Please use a subclass")

    # actions requested
    def pause(self):
        log.info("Received request to pause")
        asyncio.create_task(self._fork_and_report(
            self._pause_cmd,
            self._fetch_state,
            partial(self._report_state, show=False, suggest_sync=None),
        ))

    def resume(self):
        log.info("Received request to resume")
        asyncio.create_task(self._fork_and_report(
            self._resume_cmd,
            self._fetch_state,
            partial(self._report_state, show=False, suggest_sync=None),
        ))

    def seek(self, seek_dst):
        adjusted_seek = seek_dst + self.offset
        log.info(f"Received request to seek to {adjusted_seek}")
        asyncio.create_task(self._fork_and_report(
            self._seek_cmd.format(seek=adjusted_seek),
            self._fetch_position,
            self._report_state,
        ))

    # periodic poll/report
    async def _report_state(
        self, *,
        show=False, suggest_sync: Optional[SyncSuggestion] = None,
    ):
        """:param show: A recommendation whether to explicitly log on
                        the subscriber side

        """
        log.debug(f"Reporting state with {suggest_sync=}")
        if self._length:
            adjusted_position = self._position - self.offset
        else:
            adjusted_position = self._position
        await self._sock.emit("update state", {
            "title": self._title,
            "status": self._state.value,
            "position": "{}/{}".format(adjusted_position, self._length),
            "show": show,
            "suggest_sync": suggest_sync.value if suggest_sync else None,
        })

    async def _fork_and_report(self, fork_cmd, *callbacks):
        await self._fork_process(fork_cmd)
        for cb in callbacks:
            await cb()

    async def _fork_process(self, cmd):
        """Note that there is no timeout on the subprocesses"""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd.split(), stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT)
        except FileNotFoundError:
            log.critical(
                f"Couldn't launch the command '{cmd}'. Is it installed?")
            return ""
        stdout_data, stderr_data = await proc.communicate()
        await proc.wait()
        if proc.returncode:
            return ""
        else:
            return stdout_data.strip().decode("utf-8")

    async def _fetch_state(self) -> bool:
        status_str = await self._fork_process(self._status_cmd)
        state = PlayerState(status_str)
        changed = state != self._state
        self._state = state
        return changed

    async def _fetch_position(self, _=None):
        try:
            self._position = int(
                float(await self._fork_process(self._position_cmd)))
        except ValueError:
            self._position = 0
        return self._position

    async def _poll_and_report_metadata(self):
        state_changed = await self._fetch_state()
        fname = await self._fork_process(self._title_cmd)
        title = urllib.request.unquote(os.path.basename(fname))
        position = await self._fetch_position()
        try:
            length = int(await self._fork_process(self._length_cmd)) // 1000000
        except ValueError:
            length = 0

        if state_changed:
            suggest_sync = SyncSuggestion.STATE
            show = True
        elif title != self._title or length != self._length:
            suggest_sync = None
            show = True
        else:
            # Check seek (not implemented)
            suggest_sync = None
            show = False

        self._title = title
        self._position, self._length = position, length
        await self._report_state(show=show, suggest_sync=suggest_sync)

    async def _periodic_report_metadata(self):
        elapsed = 0
        while True:
            await asyncio.sleep(self.POLL_PERIOD_S - elapsed)
            t1 = time.perf_counter()
            await self._poll_and_report_metadata()
            elapsed = time.perf_counter() - t1
            log.debug("rescheduling poll for next iteration...")
