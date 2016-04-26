#!/usr/bin/env python3
import time

from gi.repository import Playerctl, GLib

player = Playerctl.Player(player_name='vlc')


def on_metadata(player, e):
	if 'xesam:artist' in e.keys() and 'xesam:title' in e.keys():
		print('Now playing:')
		print('metadata: {artist} - {title}'.format(
			artist=e['xesam:artist'][0], title=e['xesam:title']))


def on_play(player):
	print('Playing at volume {}'.format(player.props.volume))


def on_pause(player):
	print('Paused the song: {}'.format(player.get_title()))


def on_stop(player):
	time.sleep(0.2)
	player.play()
	player.seek(50)


def main():
	player.on('play', on_play)
	player.on('pause', on_pause)
	player.on('stop', on_stop)
	player.on('metadata', on_metadata)

	# start playing some music
	player.stop()
	time.sleep(0.2)
	player.play()

	if player.get_artist() == 'Lana Del Rey':
		# I meant some good music!
		player.next()

	# wait for events
	main = GLib.MainLoop()
	main.run()


if __name__ == '__main__':
	main()
