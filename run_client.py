#!/usr/bin/env python3
import logging
import argparse

import gi
gi.require_version('Playerctl', '1.0')  # noqa
from gi.repository import Playerctl
import asyncio
import gbulb
gbulb.install()  # noqa

from client.vlc import VLCClient
from client.websocket import DatenightWS

log = logging.getLogger(__name__)


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
	client = VLCClient(vlc_player)
	DatenightWS(client)

	asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
	main()
