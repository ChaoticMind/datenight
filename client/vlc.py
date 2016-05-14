import logging
import time

log = logging.getLogger(__name__)


class VLCClient():
	def __init__(self, player):
		self._player = player

		self._player.on('play', self._on_play)
		self._player.on('pause', self._on_pause)
		self._player.on('stop', self._on_stop)
		self._player.on('metadata', self._on_metadata)

		# start playing some music
		# self._player.play_pause()
		# print(self._player.__dict__)
		# time.sleep(0.2)
		# self._player.play()
		log.info("Initialized player")

		if self._player.get_artist() == 'Lana Del Rey':
			# I meant some good music!
			self._player.next()

	def pause(self):
		log.info("Pausing")
		self._player.pause()

	def resume(self):
		log.info("Resuming")
		self._player.play()

	def seek(self, seek_dst):
		log.info("Seeking to {}".format(seek_dst))
		self._player.set_position(seek_dst * 1000000)

	def _on_metadata(self, player, e):
		if 'xesam:artist' in e.keys() and 'xesam:title' in e.keys():
			print('Now playing:')
			print('metadata: {artist} - {title}'.format(
				artist=e['xesam:artist'][0], title=e['xesam:title']))

	def _on_play(self, player):
		print('Playing at volume {}'.format(player.props.volume))

	def _on_pause(self, player):
		print('Paused the song: {}'.format(player.get_title()))

	def _on_stop(self, player):
		time.sleep(0.2)
		player.play()
		player.seek(150)
