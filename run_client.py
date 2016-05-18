#!/usr/bin/env python3
import logging
import argparse
import asyncio
import sys

import gbulb
gbulb.install()  # noqa

from client.vlc import IntrospectiveVLCClient, ForkingPlayerctlClient, ForkingOSXClient
from client.websocket import PublishNamespace
from client.socketio_patched import SocketIOPatched

log = logging.getLogger(__name__)
__version__ = (0, 0, 1)


def main():
	if sys.platform == "linux":
		clients = ["introspective", "forking"]
		default_client = "introspective"

		clients_mapping = {
			"introspective": IntrospectiveVLCClient,
			"forking": ForkingPlayerctlClient
		}

	elif sys.platform == "osx":
		clients = ["forking"]
		default_client = "forking"

		clients_mapping = {
			"forking": ForkingOSXClient
		}

	elif sys.platform == "windows":
		print("Windows not yet supported")
		return 1
	else:
		print("Platform {} not supported".format(sys.platform))
		return 1

	# argparse setup
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='datenight client')

	# optional arguments
	parser.add_argument('-v', action='count', help="verbosity increases with each 'v' | critical/error/warning/info/debug", default=0)
	parser.add_argument('-s', '--server', type=str, default="localhost", help="hostname to connect to")
	parser.add_argument('-p', '--port', default=80, type=int, help="port to connect to")
	parser.add_argument('-c', '--client', default=default_client, type=str, choices=clients, help="Select a client to use")
	parser.add_argument('-a', '--alias', type=str, default=None, help="Name by which this publisher will be known as")
	parser.add_argument('-V', '--version', action='version', version="%(prog)s v{}".format('.'.join(map(str, __version__))), help="Show version and exit")
	# --no-gui?

	args = parser.parse_args()
	if args.client not in clients:
		# fallback if the default_client is invalid
		print("Must choose a client (-c) from {}".format(clients))
		return 1

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
	# logging.getLogger('').setLevel(logging.DEBUG)  # socketio debug

	socket_io = SocketIOPatched(host=args.server, port=args.port)
	publish = socket_io.define(PublishNamespace, path='/publish')

	loop = asyncio.get_event_loop()
	loop.call_soon(publish.regular_peek, loop)

	client = clients_mapping[args.client](publish)
	publish.client = client

	# loop.set_debug(True)
	# logging.getLogger('asyncio').setLevel(logging.DEBUG)
	loop.run_forever()


if __name__ == '__main__':
	sys.exit(main())
