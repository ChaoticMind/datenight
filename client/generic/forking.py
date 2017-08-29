import logging
import sys
import os
import urllib.request
import asyncio

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # TODO: should be in __init__()


class ForkingClient:
    """Client which forks another process to get and set properties

    Don't use this class directly, use one of its implementations instead
    Subclasses should overload the user agent (self.ua)
    and self._define_commands()

    """
    POLL_PERIOD = 0.9
    ua = "{}_forking_{}".format(sys.platform, '.'.join(map(str, _version)))

    def __init__(self, sock, offset=0):
        self._sock = sock
        self._define_commands()

        self._state = "Paused"
        self._title = ""
        self._position = 0
        self._length = 0
        self.offset = offset

        log.info("Initialized {} player".format(self.__class__.__name__))
        loop = asyncio.get_event_loop()
        self.handle = loop.call_soon(self._periodic_report_metadata)

    def _define_commands(self):
        """Subclasses should implement the following variables
        self._pause_cmd, self._resume_cmd, self._seek_cmd
        self._position_cmd, self._status_cmd, self._title_cmd, self._length_cmd

        """
        raise NotImplementedError("Please use a subclass")

    # actions requested
    def pause(self):
        log.info("Received request to pause")
        d = asyncio.ensure_future(self._fork_process(self._pause_cmd))

        def pause_helper(_):
            d2 = asyncio.ensure_future(self._fetch_state())
            d2.add_done_callback(self._report_state_show)
            return d2

        d.add_done_callback(pause_helper)

    def resume(self):
        log.info("Received request to resume")
        d = asyncio.ensure_future(self._fork_process(self._resume_cmd))

        def resume_helper(_):
            d2 = asyncio.ensure_future(self._fetch_state())
            d2.add_done_callback(self._report_state_show)
            return d2

        d.add_done_callback(resume_helper)

    def seek(self, seek_dst):
        adjusted_seek = seek_dst + self.offset
        log.info("Received request to seek to {}".format(adjusted_seek))
        d = asyncio.ensure_future(
            self._fork_process(self._seek_cmd.format(seek=adjusted_seek)))

        def seek_helper(_):
            d2 = asyncio.ensure_future(self._fetch_position())
            d2.add_done_callback(self._report_state)
            return d2

        d.add_done_callback(seek_helper)

    # periodic poll/report
    def _report_state_show(self, _):
        return self._report_state(_, show=True)

    def _report_state(self, _=None, show=False):
        """:param show: A recommendation whether to explicitly log on
                        the subscriber side

        """
        log.debug("Reporting state")
        if self._length:
            adjusted_position = self._position - self.offset
        else:
            adjusted_position = self._position
        self._sock.emit("update state", {
            "title": self._title,
            "status": self._state,
            "position": "{}/{}".format(adjusted_position, self._length),
            "show": show})

    async def _fork_process(self, cmd):
        """Note that there is no timeout on the subprocesses"""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd.split(), stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT)
        except FileNotFoundError:
            log.critical(
                "Couldn't launch the command '{}'. Is it installed?".format(
                    cmd))
            return ""
        stdout_data, stderr_data = await proc.communicate()
        await proc.wait()
        if proc.returncode:
            return ""
        else:
            return stdout_data.strip().decode("utf-8")

    async def _fetch_state(self):
        self._state = await self._fork_process(self._status_cmd)
        return self._state

    async def _fetch_position(self, _=None):
        try:
            self._position = int(
                float(await self._fork_process(self._position_cmd)))
        except ValueError:
            self._position = 0
        return self._position

    async def _poll_metadata(self):
        self.handle.cancel()
        state = await self._fetch_state()
        fname = await self._fork_process(self._title_cmd)
        title = urllib.request.unquote(os.path.basename(fname))
        position = await self._fetch_position()
        try:
            length = int(await self._fork_process(self._length_cmd)) // 1000000
        except ValueError:
            length = 0

        if (state != self._state or
                title != self._title or
                length != self._length):
            show = True
        else:
            show = False

        self._state, self._title = state, title
        self._position, self._length = position, length

        self._report_state(show=show)
        loop = asyncio.get_event_loop()
        log.debug("rescheduling poll for next iteration...")
        self.handle = loop.call_later(self.POLL_PERIOD,
                                      self._periodic_report_metadata)

    def _periodic_report_metadata(self):
        asyncio.ensure_future(self._poll_metadata())
