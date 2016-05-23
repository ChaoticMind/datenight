#!/usr/bin/env python3
import logging
import argparse
import asyncio
import sys
import subprocess

from client.vlc import IntrospectiveVLCClient, ForkingPlayerctlClient, UnixSocketClient, _version
from client.websocket import PublishNamespace
from client.socketio_patched import SocketIOPatched

log = logging.getLogger(__name__)


def main():
	if sys.platform == "linux":
		clients = {
			"introspective": IntrospectiveVLCClient,
			"playerctl": ForkingPlayerctlClient,
			# "socat": ForkingSocatClient,
			# "netcat": ForkingNetcatClient
			"unixsocket": UnixSocketClient
		}
		default_client = "introspective"

	elif sys.platform == "osx":
		clients = {
			"unixsocket": UnixSocketClient
			# "netcat": ForkingNetcatClient
		}
		default_client = "netcat"

	elif sys.platform == "windows":
		print("windows not yet supported")
		loop = asyncio.ProactorEventLoop()  # for subprocesses on windows
		asyncio.set_event_loop(loop)
		return 1
	else:
		print("Platform {} not supported".format(sys.platform))
		return 1

	def get_commit_id():
		# called on every launch, but that's ok for now
		return subprocess.run(["git", "describe", "--always"], stdout=subprocess.PIPE, timeout=0.5).stdout.decode('utf-8').strip()

	# argparse setup
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='datenight client')

	# optional arguments
	parser.add_argument('-v', action='count', help="verbosity increases with each 'v' | critical/error/warning/info/debug", default=0)
	parser.add_argument('-s', '--server', type=str, default="localhost", help="hostname to connect to")
	parser.add_argument('-p', '--port', default=None, type=int, help="port to connect to (if unspecified, defaults to 80 for http:// and 443 for https://)")
	parser.add_argument('-c', '--client', default=default_client, type=str, choices=clients.keys(), help="Select a client to use")
	parser.add_argument('-a', '--alias', type=str, default=None, help="Name by which this publisher will be known as")
	parser.add_argument('-V', '--version', action='version', version="%(prog)s v{} ({})".format('.'.join(map(str, _version)), get_commit_id()), help="Show version and exit")

	args = parser.parse_args()
	if args.client not in clients:
		# fallback if the default_client is invalid
		print("Must choose a client (-c) from {}".format(clients.keys()))
		return 1
	if args.client == "introspective":
		try:
			import gbulb
		except ImportError:
			print(
				"You don't have the gbulb module installed (needed for the introspective client)\n"
				"Install it or use an alternative client with the -c flag")
			return 1
		else:
			gbulb.install()

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
	if args.port is None:
		if args.server.startswith("https"):
			args.port = 443
		elif args.server.startswith("http"):
			args.port = 80
	socket_io = SocketIOPatched(host=args.server, port=args.port)
	publish = socket_io.define(PublishNamespace, path='/publish')
	if args.alias:
		publish.update_alias(args.alias)

	loop = asyncio.get_event_loop()
	loop.call_soon(publish.regular_peek, loop)

	client = clients[args.client](publish)
	publish.initialize_namespace(client)

	# loop.set_debug(True)
	# logging.getLogger('asyncio').setLevel(logging.DEBUG)
	loop.run_forever()


if __name__ == '__main__':
	sys.exit(main())
