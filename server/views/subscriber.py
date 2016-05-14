import logging
import random

from flask import request
from flask.ext.socketio import emit

from server import socketio, publishers, subscribers, subscribers_nick_presets
from server.helpers import clean_publishers

log = logging.getLogger(__name__)


# subscribe
@socketio.on('connect', namespace='/subscribe')
def connect_subscriber():
	log.info("Connecting subscriber {}".format(request.sid))
	other_subscriber_nicks = {z['nick'] for z in subscribers.values()}
	other_nicks = other_subscriber_nicks.union({z.nick for z in publishers.values()})

	if request.sid in subscribers:
		raise RuntimeError("{} (subscriber) Connected twice.".format(request.sid))
	for i in range(10):
		# x = str(random.randint(1, 10000))
		x = random.choice(subscribers_nick_presets)
		if x not in other_nicks:
			subscribers[request.sid] = {"nick": x}
			other_subscriber_nicks.add(x)
			other_nicks.add(x)
			break
	else:
		log.info("Couldn't assign a nick, disconnecting the subscriber...")
		emit("log message", {"data": "Failed to assign you a nick", "fatal": True})
		return

	log.info("Someone (id={}, nick={}) just subscribed! - total: {}".format(request.sid, x, len(subscribers)))
	emit('nick change', {'new': x, 'old': None, 'complete': list(other_subscriber_nicks)}, broadcast=False)
	emit('update subscriptions', {'complete': list(other_subscriber_nicks), 'new': x, 'old': None}, broadcast=True, include_self=False)

	emit('update publishers', {'data': clean_publishers()})
	return True


@socketio.on("help", namespace='/subscribe')
def display_help(_):
	log.info("help requested")
	emit("log message", {"data": 'Commands are: "/help" "/nick &lt;nick&gt;", "/pause"'})


@socketio.on("pause", namespace='/subscribe')
def request_pause(_):
	log.info("pause requested by {}".format(request.sid))
	requester_nick = subscribers[request.sid]['nick']
	emit("log message", {"data": 'Pause requested by "{}"'.format(requester_nick)}, namespace="/subscribe", broadcast=True, include_self=True)
	emit("pause", namespace="/publish", broadcast=True)


@socketio.on("change nick", namespace='/subscribe')
def update_nick(msg):
	log.info("nick change requested")
	log.info(request.event)

	subscribers_nicks = {z['nick'] for z in subscribers.values()}
	old_nick = subscribers[request.sid]['nick']
	try:
		new_nick = msg['new']
	except KeyError:
		emit("log message", {"data": "obey the API!".format(new_nick)})
		return
	if old_nick == new_nick:
		emit("log message", {"data": "Your nick is already {}".format(new_nick)})
		return
	else:
		other_nicks = subscribers_nicks.union({z.nick for z in publishers.values()})
		if new_nick in other_nicks:
			emit("log message", {"data": "Nick {} already exists".format(new_nick)})
			return

	subscribers[request.sid]['nick'] = new_nick
	subscribers_nicks = {z['nick'] for z in subscribers.values()}

	emit('nick change', {'new': new_nick, 'old': old_nick, 'complete': list(subscribers_nicks)}, broadcast=False)
	emit("update subscriptions", {'complete': list(subscribers_nicks), 'new': new_nick, 'old': old_nick}, broadcast=True, include_self=False)


@socketio.on('broadcast message', namespace='/subscribe')
def broadcast_message(message):
	log.info("Subscriber broadcasting: {}".format(message))
	nick = subscribers[request.sid]['nick']
	try:
		content = message['data']
	except KeyError:
		pass
	else:
		emit('log message', {'data': content, 'nick': nick}, broadcast=True, include_self=False)
		return message['data']


@socketio.on('disconnect', namespace='/subscribe')
def disconnect_subscriber():
	try:
		old_nick = subscribers[request.sid]['nick']
		del subscribers[request.sid]
	except KeyError:  # nick was never assigned
		log.info('subscriber {} just disconnected without a nick ever been assigned - total: {}'.format(request.sid, len(subscribers)))
	else:
		subscribers_nicks = {z['nick'] for z in subscribers.values()}

		log.info('subscriber {} just disconnected - total: {}'.format(request.sid, len(subscribers)))
		emit('update subscriptions', {'complete': list(subscribers_nicks), 'new': None, 'old': old_nick}, broadcast=True)
