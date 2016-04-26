import logging
import random

from flask import request
from flask.ext.socketio import emit, disconnect

from server import socketio, publishers, subscribers
from server.helpers import clean_publishers

log = logging.getLogger(__name__)


# publish
@socketio.on('connect', namespace='/publish')
def connect_publisher():
	log.info("Connecting publisher {}".format(request.sid))
	other_publisher_nicks = {z['nick'] for z in publishers.values()}
	other_nicks = other_publisher_nicks.union({z['nick'] for z in subscribers.values()})

	if request.sid in publishers:
		raise RuntimeError("{} (publisher) Connected twice.".format(request.sid))
	for i in range(10):
		x = str(random.randint(1, 10000))
		if x not in other_nicks:
			publishers[request.sid] = {"nick": x}
			other_publisher_nicks.add(x)
			other_nicks.add(x)
			break
	else:
		log.info("Couldn't assign a nick, disconnecting the publisher...")
		emit("log message", {"data": "Failed to assign you a nick", "fatal": True})
		return

	log.info("A publisher just connected (id={}, nick={}) - total publishers: {}) connected to control".format(request.sid, x, len(publishers)))
	emit('update publishers', {'data': clean_publishers(), 'new': x, 'old': None}, namespace='/subscribe', broadcast=True)


@socketio.on('update state', namespace='/publish')
def message_trigger(message):
	log.info("Publisher state updated: {}".format(message))
	nick = publishers[request.sid]['nick']
	publishers[request.sid].update(message)
	emit('update publishers', {'data': clean_publishers(), 'update': nick}, namespace='/subscribe', broadcast=True)


# @socketio.on('publisher_debug', namespace='/publish')
# def player_debug(message):
# 	log.info("Publisher broadcasting: {}".format(message))
# 	emit('log message', {'data': message['data']}, namespace='/subscribe', broadcast=True)
# 	emit('log message', {'data': message['data']}, broadcast=True)


@socketio.on('disconnect request', namespace='/publish')
def disconnect_request():
	log.info('publisher asked for a disconnect, disconnecting...')
	disconnect()


@socketio.on('disconnect', namespace='/publish')
def disconnect_publisher():
	try:
		old_nick = publishers[request.sid]['nick']
		del publishers[request.sid]
	except KeyError:  # nick was never assigned
		log.info('publisher {} just disconnected without a nick ever been assigned - total: {}'.format(request.sid, len(publishers)))
	else:
		log.info('publisher {} just disconnected - total: {}'.format(request.sid, len(publishers)))
		emit('update publishers', {'data': clean_publishers(), 'new': None, 'old': old_nick}, namespace='/subscribe', broadcast=True)
