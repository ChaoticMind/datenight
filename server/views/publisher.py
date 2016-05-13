import logging
import random
import time
import json

import eventlet
from flask import request
from flask.ext.socketio import emit, disconnect

from server import socketio, publishers, subscribers
from server.helpers import clean_publishers

log = logging.getLogger(__name__)


class Publisher():
	ping_delay = 5
	timeout_threshold = 60

	def __init__(self, sid, nick):
		self.__sid = sid
		self.nick = nick
		self.latency = -1
		self.status = 'stopped'
		self.position = -1
		self.__ping_token = None
		self.__ping_ts = None
		self.__heartbeat = eventlet.greenthread.spawn(self.__ping)
		self.__timeout = eventlet.greenthread.spawn_after(self.timeout_threshold, self.__timeout)

	def __ping(self):
		log.debug("{}: ping request".format(self.__sid))
		self.__ping_token = random.randint(1, 10000000)
		self.__ping_ts = time.time()
		socketio.emit('latency_ping', {"token": self.__ping_token}, namespace='/publish', room=self.__sid)
		self.__heartbeat = eventlet.greenthread.spawn_after(self.ping_delay, self.__ping)

	def __timeout(self):
		log.info("{}: no ping reply in {} seconds, setting latency to -1".format(self.__sid, self.timeout_threshold))
		self.latency = -1
		self.__timeout = eventlet.greenthread.spawn_after(self.timeout_threshold, self.__timeout)

	def pong(self, token):
		log.debug("{}: pong received".format(self.__sid))
		if not self.__ping_token == token:
			log.warning("{}: Invalid token, ignoring...".format(self.__sid))
			return
		self.latency = round(time.time() - self.__ping_ts, 3)
		socketio.emit('update publishers', {'data': clean_publishers(), 'update': self.nick, 'show': False}, namespace='/subscribe', broadcast=True)

		# reset timeout
		self.__timeout.cancel()
		self.__timeout = eventlet.greenthread.spawn_after(self.timeout_threshold, self.__timeout)

	def dict_repr(self):
		"""Don't expose private data, this is sent over the wire"""
		return {'status': self.status, 'position': self.position, 'latency': self.latency}

	def remove_timeouts(self):
		log.info("Removing timers from {}".format(self.__sid))
		self.__heartbeat.cancel()
		self.__timeout.cancel()

	def __repr__(self):
		return json.dumps(self.dict_repr())

	def __del__(self):
		self.remove_timeouts()


# publish
@socketio.on('connect', namespace='/publish')
def connect_publisher():
	log.info("Connecting publisher {}".format(request.sid))
	other_publisher_nicks = {z.nick for z in publishers.values()}
	other_nicks = other_publisher_nicks.union({z['nick'] for z in subscribers.values()})

	if request.sid in publishers:
		raise RuntimeError("{} (publisher) Connected twice.".format(request.sid))
	for i in range(10):
		x = str(random.randint(1, 10000))
		if x not in other_nicks:
			publishers[request.sid] = Publisher(sid=request.sid, nick=x)
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
	nick = publishers[request.sid].nick
	publishers[request.sid].status = message['status']
	publishers[request.sid].position = message['position']
	emit('update publishers', {'data': clean_publishers(), 'update': nick, 'show': True}, namespace='/subscribe', broadcast=True)


@socketio.on('latency_pong', namespace='/publish')
def ping(message):
	try:
		publishers[request.sid].pong(message['token'])
	except KeyError:
		emit("log message", {"data": "Received bad pong", "fatal": True})


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
		old_nick = publishers[request.sid].nick
		publishers[request.sid].remove_timeouts()
		del publishers[request.sid]
	except KeyError:  # nick was never assigned
		log.info('publisher {} just disconnected without a nick ever been assigned - total: {}'.format(request.sid, len(publishers)))
	else:
		log.info('publisher {} just disconnected - total: {}'.format(request.sid, len(publishers)))
		emit('update publishers', {'data': clean_publishers(), 'new': None, 'old': old_nick}, namespace='/subscribe', broadcast=True)
