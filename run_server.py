#!/usr/bin/env python3
import logging
import argparse

from server import app, socketio


def main():
	# argparse setup
	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='datenight server')

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

	logger = logging.getLogger('server')
	logger.setLevel(level)
	logger.addHandler(sh)

	# run flask
	socketio.run(app, debug=True)
	# socketio.run(app, host='0.0.0.0', port=5500, debug=False)


if __name__ == '__main__':
	main()
