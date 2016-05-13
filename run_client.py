#!/usr/bin/env python3
import logging
import argparse

import gi
gi.require_version('Playerctl', '1.0')
from gi.repository import Playerctl, GLib  # noqa

from client.vlc import VLCClient  # noqa


def main():
	# argparse setup
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='datenight client')

	# optional arguments
	parser.add_argument('-v', action='count', help="verbosity increases with each 'v' | critical/error/warning/info/debug", default=0)

	args = parser.parse_args()

	# logger setup
	level = max(10, 50 - (10 * args.v))
	print('Logging level is: {}'.format(logging.getLevelName(level)))
	logger = logging.getLogger(__name__)
	logger.setLevel(level)
	formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t%(message)s')
	sh = logging.StreamHandler()
	sh.setFormatter(formatter)
	logger.addHandler(sh)

	logger = logging.getLogger('client')
	logger.setLevel(level)
	logger.addHandler(sh)

	# main loop
	vlc_player = Playerctl.Player(player_name='vlc')
	# generic_player = Playerctl.Player()  # generic client
	VLCClient(vlc_player)
	main = GLib.MainLoop()
	main.run()


if __name__ == '__main__':
	main()
