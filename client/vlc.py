import logging
import time

log = logging.getLogger(__name__)


class VLCClient():
	def __init__(self, player):
		self.player = player

		self.player.on('play', self._on_play)
		self.player.on('pause', self._on_pause)
		self.player.on('stop', self._on_stop)
		self.player.on('metadata', self._on_metadata)

		# start playing some music
		# self.player.play_pause()
		# print(self.player.__dict__)
		# time.sleep(0.2)
		# self.player.play()
		log.info("Initialized player")

		if self.player.get_artist() == 'Lana Del Rey':
			# I meant some good music!
			self.player.next()

	def pause(self):
		log.info("Pausing")
		self.player.pause()

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
		player.seek(50)
