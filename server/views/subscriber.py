import logging
import random

from flask import request
from flask_socketio import emit

from server import socketio, publishers, subscribers, subscribers_nick_presets
from server import current_state, STATE_NAMES, PLAYING, PAUSED
from server.helpers import clean_publishers

log = logging.getLogger(__name__)


class Subscriber:
    def __init__(self, nick):
        # self.ua = "unknown"
        self.nick = nick
        # self.color = color


# subscribe
@socketio.on('connect', namespace='/subscribe')
def connect_subscriber():
    log.info("Connecting subscriber {}".format(request.sid))
    other_subscriber_nicks = {z.nick for z in subscribers.values()}
    other_nicks = other_subscriber_nicks.union(
        {z.nick for z in publishers.values()})

    if request.sid in subscribers:
        raise RuntimeError(
            "{} (subscriber) Connected twice.".format(request.sid))
    for i in range(10):
        # x = str(random.randint(1, 10000))
        x = random.choice(subscribers_nick_presets)
        if x not in other_nicks:
            subscribers[request.sid] = Subscriber(nick=x)
            other_subscriber_nicks.add(x)
            other_nicks.add(x)
            break
    else:
        log.info("Couldn't assign a nick, disconnecting the subscriber...")
        emit("log message",
             {"data": "Failed to assign you a nick", "fatal": True})
        return

    log.info("Someone (id={}, nick={}) just subscribed! - total: {}".format(
        request.sid, x, len(subscribers)))
    emit('nick change',
         {'new': x, 'old': None, 'complete': list(other_subscriber_nicks)},
         broadcast=False)
    emit('update subscriptions',
         {'complete': list(other_subscriber_nicks), 'new': x, 'old': None},
         broadcast=True, include_self=False)

    emit('update publishers',
         {'data': clean_publishers(), 'state': STATE_NAMES[current_state]})
    return True


@socketio.on("help", namespace='/subscribe')
def display_help(_):
    log.info("help requested")
    emit("log message", {
        "data": 'Commands are: "/help" "/nick <new_nick>", "/pause", "/resume"'
                ', "/seek <int>"'})


@socketio.on("pause", namespace='/subscribe')
def request_pause(_):
    log.info("pause requested by {}".format(request.sid))
    requester_nick = subscribers[request.sid].nick
    global current_state
    current_state = PAUSED
    emit(
        "log message", {
            "data": 'Pause requested by "{}"'.format(requester_nick),
            "state": STATE_NAMES[current_state]
        }, namespace="/subscribe", broadcast=True, include_self=True)
    emit("pause", namespace="/publish", broadcast=True)


@socketio.on("resume", namespace='/subscribe')
def request_resume(_):
    log.info("resume requested by {}".format(request.sid))
    requester_nick = subscribers[request.sid].nick
    global current_state
    current_state = PLAYING
    emit(
        "log message", {
            "data": 'Resume requested by "{}"'.format(requester_nick),
            "state": STATE_NAMES[current_state]
        }, namespace="/subscribe", broadcast=True, include_self=True)
    emit("resume", namespace="/publish", broadcast=True)


@socketio.on("seek", namespace='/subscribe')
def request_seek(dst):
    log.info("seek requested to {} by {}".format(dst, request.sid))
    requester_nick = subscribers[request.sid].nick
    try:
        seek_dst = int(dst['seek'])
    except (KeyError, ValueError):
        emit("log message", {
            "data": 'Invalid seek requested ({}). Must be in seconds.'.format(
                dst['seek'])}, namespace="/subscribe")
        return
    else:
        emit("log message", {
            "data": 'Seek requested to {} by "{}"'.format(seek_dst,
                                                          requester_nick)},
             namespace="/subscribe", broadcast=True, include_self=True)
        emit("seek", {"seek": seek_dst}, namespace="/publish", broadcast=True)


@socketio.on("change nick", namespace='/subscribe')
def change_nick(msg):
    log.info("subscriber nick change requested")
    # log.info(request.event)

    old_nick = subscribers[request.sid].nick
    try:
        new_nick = msg['new']
    except KeyError:
        emit("log message", {"data": "obey the API! (missing key 'new')"})
        return
    if old_nick == new_nick:
        emit("log message",
             {"data": 'Your nick is already "{}"'.format(new_nick)})
        return
    else:
        subscribers_nicks = {z.nick for z in subscribers.values()}
        other_nicks = subscribers_nicks.union(
            {z.nick for z in publishers.values()})
        if new_nick in other_nicks:
            emit("log message",
                 {"data": "Nick {} already exists".format(new_nick)})
            return

    subscribers[request.sid].nick = new_nick
    subscribers_nicks.remove(old_nick)
    subscribers_nicks.add(new_nick)

    emit('nick change', {'new': new_nick, 'old': old_nick,
                         'complete': list(subscribers_nicks)}, broadcast=False)
    emit("update subscriptions",
         {'complete': list(subscribers_nicks), 'new': new_nick,
          'old': old_nick}, broadcast=True, include_self=False)


@socketio.on('broadcast message', namespace='/subscribe')
def broadcast_message(message):
    """A chat message to other subscribers"""
    log.info("Subscriber broadcasting: {}".format(message))
    nick = subscribers[request.sid].nick
    try:
        content = message['data']
    except KeyError:
        pass
    else:
        emit('log message', {'data': content, 'nick': nick}, broadcast=True,
             include_self=False)
        return message['data']


@socketio.on('disconnect', namespace='/subscribe')
def disconnect_subscriber():
    try:
        old_nick = subscribers[request.sid].nick
        del subscribers[request.sid]
    except KeyError:  # nick was never assigned
        log.info(
            'subscriber {} just disconnected without a nick having ever been'
            ' assigned - total: {}'.format(
                request.sid, len(subscribers)))
    else:
        subscribers_nicks = {z.nick for z in subscribers.values()}

        log.info(
            'subscriber {} just disconnected - total: {}'.format(
                request.sid, len(subscribers)))
        emit('update subscriptions',
             {'complete': list(subscribers_nicks), 'new': None,
              'old': old_nick}, broadcast=True)
