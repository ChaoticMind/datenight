import logging
import os
import urllib.request

import gi
gi.require_version('Playerctl', '1.0')  # noqa
from gi.repository import Playerctl

log = logging.getLogger(__name__)


class VLCClient():
	def __init__(self, sock, loop):
		self._sock = sock

		self._state = "Paused"
		self._title = ""
		self._position = -1
		self._length = -1

		self.__initialize_player()

		log.info("Initialized player")
		initial_metadata = self._player.get_property("metadata")
		if initial_metadata:
			self._on_metadata(self._player, initial_metadata)  # set metadata

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
		loop.call_later(1, self._periodic_report_position, loop)

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
		self._player.pause()

	def resume(self):
		log.info("Received request to resume")
		self._player.play()

	def seek(self, seek_dst):
		log.info("Received request to seek to {}".format(seek_dst))
		self._player.set_position(seek_dst * 1000000)

	# events occurred
	def _on_metadata(self, player, e):
		log.debug("New metadata: {}".format(e))
		# set title
		if 'xesam:artist' in e.keys() and 'xesam:title' in e.keys():  # music
			log.info('Now playing track: {artist} - {title}'.format(
				artist=e['xesam:artist'][0], title=e['xesam:title']))
			self._title = player.get_title()
		elif 'xesam:title' in e.keys():  # vid with metadata
			self._title = player.get_title()
			log.info('Now playing file: {}'.format(self._title))
		elif 'xesam:url' in e.keys():  # arbitrary file
			fname = os.path.basename(e['xesam:url'])
			self._title = urllib.request.unquote(fname)
			log.info('Now playing file: {}'.format(self._title))
		else:
			if self._player.get_property("status") == "Stopped":
				self._title = ""
				# self._on_stop(player)
			else:
				self._title = "?"
				log.info('Now playing unknown file')

		# get length
		if 'mpris:length' in e.keys():
			self._length = int(e['mpris:length']) // 1000000

	def _on_play(self, player):
		log.info("Playing: {}".format(self._title))
		self._state = "Playing"
		self._report_position(show=True)

	def _on_pause(self, player):
		log.info("Paused: {}".format(self._title))
		self._state = "Paused"
		self._report_position(show=True)

	def _on_stop(self, player):
		log.info("Player is stopped...")
		self._state = "Stopped"
		self._report_position(show=True)

	def _on_exit(self, player):
		self._title = ""
		self._length = -1
		return self._on_stop(player)

	# periodic report
	def _report_position(self, show=False):
		"""show is a recommendation to explicitely log on the subscriber side"""
		self.__initialize_player()
		self._position = self._player.get_property("position") // 1000000
		self._sock.emit("update state", {
			"title": self._title,
			"status": self._state,
			"position": "{}/{}".format(self._position, self._length),
			"show": show})

	def _periodic_report_position(self, loop):
		self._report_position()
		loop.call_later(1, self._periodic_report_position, loop)
