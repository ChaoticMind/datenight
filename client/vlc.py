import logging
import os
import urllib.request
import asyncio
# from functools import partial

import gi
gi.require_version('Playerctl', '1.0')  # noqa
from gi.repository import GLib, Playerctl

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # should be in __init__()


class IntrospectiveVLCClient():
	"""Uses GLib introspection library (see playerctl documentation)"""
	REPORT_PERIOD = 1
	ua = "linux_introspective_{}".format('.'.join(map(str, _version)))

	def __init__(self, sock):
		self._sock = sock

		self._state = "Paused"
		self._title = ""
		self._position = -1
		self._length = -1

		self.__initialize_player()

		log.info("Initialized {} player".format(self.__class__.__name__))
		loop = asyncio.get_event_loop()
		self.handle = loop.call_soon(self._report_and_reschedule)  # not necessary since _on_stop/_on_play/_on_pause are called next, but just in case.

		initial_metadata = self._player.get_property("metadata")
		if initial_metadata:
			self._on_metadata(self._player, initial_metadata, dontsend=True)  # set metadata

		if self._title:
			log.info("Player is running with {}".format(self._title))
			if self._player.get_property("status") == "Playing":
				self._on_play(self._player)  # set state etc
			elif self._player.get_property("status") == "Paused":
				self._on_pause(self._player)  # set state etc
			else:
				log.error("Player in unknown state")
		else:
			self._on_stop(self._player)  # set state etc

	def __initialize_player(self):
		self._player = Playerctl.Player(player_name='vlc')
		self._player.on('play', self._on_play)
		self._player.on('pause', self._on_pause)
		self._player.on('stop', self._on_stop)
		self._player.on('exit', self._on_exit)
		self._player.on('metadata', self._on_metadata)

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
		log.info("Received request to seek to {}".format(seek_dst))
		try:
			self._player.set_position(seek_dst * 1000000)
		except GLib.GError:
			log.error("Can't seek current file (if any)")
		except OverflowError:
			log.warning("seek destination too large, ignoring...")
		else:
			self._report_and_reschedule(show=False)  # no on_properties_changed in the lib (yet)

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
			length = -1

		if (title != self._title) or (length and (length != self._length)):
			self._title = title
			if length:
				self._length = length
			if not dontsend:
				self._report_and_reschedule(show=False)  # too spammy on file change if show

	def _on_play(self, player):
		log.info("Playing: {}".format(self._title))
		self._state = "Playing"
		self._report_and_reschedule(show=True)

	def _on_pause(self, player):
		log.info("Paused: {}".format(self._title))
		self._state = "Paused"
		self._report_and_reschedule(show=True)

	def _on_stop(self, player):
		log.info("Player is stopped...")
		self._state = "Stopped"
		self._report_and_reschedule(show=True)

	def _on_exit(self, player):
		self._title = ""
		self._length = -1
		return self._on_stop(player)

	# periodic report
	def _report_and_reschedule(self, show=False):
		""":param show: A recommendation whether explicitely log on the subscriber side"""
		self.handle.cancel()

		self.__initialize_player()
		self._position = self._player.get_property("position") // 1000000
		log.debug("Reporting state")
		self._sock.emit("update state", {
			"title": self._title,
			"status": self._state,
			"position": "{}/{}".format(self._position, self._length),
			"show": show})

		loop = asyncio.get_event_loop()
		self.handle = loop.call_later(self.REPORT_PERIOD, self._report_and_reschedule)


class ForkingVLCClient():
	"""VLC client which forks another process to get and set properties

	Don't use this class directly, use one of its implementations instead

	"""
	POLL_PERIOD = 0.9
	ua = "forking_{}".format('.'.join(map(str, _version)))

	def __init__(self, sock):
		self._sock = sock
		self._define_commands()

		self._state = "Paused"
		self._title = ""
		self._position = -1
		self._length = -1

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
			return asyncio.ensure_future(self._poll_metadata())

		d.add_done_callback(pause_helper)

	def resume(self):
		log.info("Received request to resume")
		d = asyncio.ensure_future(self._fork_process(self._resume_cmd))

		def resume_helper(_):
			return asyncio.ensure_future(self._poll_metadata())

		d.add_done_callback(resume_helper)

	def seek(self, seek_dst):
		log.info("Received request to seek to {}".format(seek_dst))
		d = asyncio.ensure_future(self._fork_process(self._seek_cmd.format(seek=seek_dst)))

		def seek_helper(_):
			d2 = asyncio.ensure_future(self._fetch_position())

			def seek_helper_helper(__):
				"""Are add_done_callback() not chained?"""
				self._report_state()

			d2.add_done_callback(seek_helper_helper)
			return d2

		d.add_done_callback(seek_helper)
		# d.add_done_callback(self._report_state)  # note: this doesn't work, made seek_helper_helper instead

	# periodic poll/report
	def _report_state(self, _=None, show=False):
		""":param show: A recommendation whether explicitely log on the subscriber side"""
		log.debug("Reporting state")
		self._sock.emit("update state", {
			"title": self._title,
			"status": self._state,
			"position": "{}/{}".format(self._position, self._length),
			"show": show})

		self.handle.cancel()
		loop = asyncio.get_event_loop()
		self.handle = loop.call_later(self.POLL_PERIOD, self._periodic_report_metadata)

	async def _fork_process(self, cmd):
		"""Note that there is no timeout on the subprocesses"""
		proc = await asyncio.create_subprocess_exec(*cmd.split(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
		stdout_data, stderr_data = await proc.communicate()
		await proc.wait()
		if proc.returncode:
			return ""
		else:
			return stdout_data.strip().decode("utf-8")

	async def _fetch_position(self, _=None):
		self._position = int(float(await self._fork_process(self._position_cmd)))
		return self._position

	async def _poll_metadata(self):
		state = await self._fork_process(self._status_cmd)
		fname = await self._fork_process(self._title_cmd)
		title = urllib.request.unquote(os.path.basename(fname))
		position = await self._fetch_position()
		try:
			length = int(await self._fork_process(self._length_cmd)) // 1000000
		except ValueError:
			length = -1

		if state != self._state or title != self._title or length != self._length:
			show = True
		else:
			show = False

		self._state, self._title, self._position, self._length = state, title, position, length

		self._report_state(show=show)

	def _periodic_report_metadata(self):
		asyncio.ensure_future(self._poll_metadata())


class ForkingPlayerctlClient(ForkingVLCClient):
	ua = "playerctl_forking_{}".format('.'.join(map(str, _version)))

	def _define_commands(self):
		self._pause_cmd = "playerctl -p vlc pause"
		self._resume_cmd = "playerctl -p vlc play"
		self._seek_cmd = "playerctl -p vlc position {seek}"

		self._position_cmd = "playerctl -p vlc position"
		self._status_cmd = "playerctl -p vlc status"
		self._title_cmd = "playerctl -p vlc metadata xesam:url"
		self._length_cmd = "playerctl -p vlc metadata mpris:length"


class ForkingOSXClient(ForkingVLCClient):
	ua = "osx_forking_{}".format('.'.join(map(str, _version)))
