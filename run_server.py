#!/usr/bin/env python3
import logging
import argparse

from server import app, socketio

log = logging.getLogger(__name__)
__version__ = (0, 0, 1)


def main():
	# argparse setup
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='datenight server')

	# optional arguments
	parser.add_argument('-v', action='count', help="verbosity increases with each 'v' | critical/error/warning/info/debug", default=0)
	parser.add_argument('-a', '--all-interfaces', action="store_true", help="Listen on 0.0.0.0? (otherwise 127.0.0.1)")
	parser.add_argument('-p', '--port', default=5500, type=int, help="port to listen on")
	parser.add_argument('-d', '--debug', action="store_true", help="run in debug mode (Warning: don't run this with -a)")
	parser.add_argument('-V', '--version', action='version', version="%(prog)s v{}".format('.'.join(map(str, __version__))), help="Show version and exit")

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

	logger = logging.getLogger('server')
	logger.setLevel(level)
	logger.addHandler(sh)

	# run flask
	host = "0.0.0.0" if args.all_interfaces else "127.0.0.1"
	socketio.run(app, host=host, port=args.port, debug=args.debug)


if __name__ == '__main__':
	main()
