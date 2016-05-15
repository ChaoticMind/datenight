#!/usr/bin/env python3
import logging
import argparse
import asyncio

import gbulb
gbulb.install()  # noqa

from client.vlc import VLCClient
from client.websocket import PublishNamespace
from client.socketio_patched import SocketIOPatched

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
	logging.getLogger('').setLevel(logging.DEBUG)  # socketio debug

	socket_io = SocketIOPatched('localhost', port=5000)
	publish = socket_io.define(PublishNamespace, '/publish')

	loop = asyncio.get_event_loop()
	loop.call_soon(publish.regular_peek, loop)

	loop = asyncio.get_event_loop()
	client = VLCClient(publish, loop)
	publish.client = client

	loop.run_forever()


if __name__ == '__main__':
	main()
