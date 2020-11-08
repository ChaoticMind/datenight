import logging
import random

from flask import request
from flask_socketio import emit

from server import socketio, publishers, subscribers
from server import current_state, STATE_NAMES, PLAYING, PAUSED
from server import subscribers_nick_presets, subscribers_color_presets
from server.helpers import clean_publishers, clean_subscribers

log = logging.getLogger(__name__)


class Subscriber:
    def __init__(self, nick, color):
        # self.ua = "unknown"
        self.nick = nick
        self.color = color

    def dict_repr(self):
        """Don't expose private data, this is sent over the wire"""
        return {'color': self.color}


# subscribe
@socketio.on('connect', namespace='/subscribe')
def connect_subscriber():
    log.info(f"Connecting subscriber {request.sid}")
    other_nicks = {z.nick for z in subscribers.values()}.union(
        {z.nick for z in publishers.values()})

    if request.sid in subscribers:
        raise RuntimeError(f"{request.sid} (subscriber) Connected twice.")

    nicks_pool = subscribers_nick_presets
    for used_nick in other_nicks:
        try:
            nicks_pool.remove(used_nick)
        except ValueError:  # user is using a non-preset nick
            pass

    colors_pool = subscribers_color_presets
    for used_color in {z.color for z in subscribers.values()}:
        try:
            colors_pool.remove(used_color)
        except ValueError:  # user is using a non-preset color
            pass

    if nicks_pool and colors_pool:
        assigned_nick = random.choice(nicks_pool)
        assigned_color = random.choice(colors_pool)
        subscribers[request.sid] = Subscriber(
            nick=assigned_nick, color=assigned_color)
    else:
        log.info("Couldn't assign a nick, disconnecting the subscriber...")
        emit("log_message",
             {"data": "Failed to assign you a nick", "fatal": True})
        return

    log.info("Someone (id={}, nick={}) just subscribed! - total: {}".format(
        request.sid, assigned_nick, len(subscribers)))
    emit(
        'nick change', {
            'new': assigned_nick, 'old': None,
            "color": assigned_color, 'complete': clean_subscribers(),
        }, broadcast=False)
    emit('update subscriptions',
         {'complete': clean_subscribers(), 'new': assigned_nick, 'old': None},
         broadcast=True, include_self=False)

    emit('update publishers',
         {'data': clean_publishers(), 'state': STATE_NAMES[current_state]})
    return True


@socketio.on("help", namespace='/subscribe')
def display_help(_):
    log.info("help requested")
    emit("log_message", {
        "data": 'Commands are: "/help" "/nick <new_nick>", "/pause", "/resume"'
                ', "/seek <int>"'})


@socketio.on("pause", namespace='/subscribe')
def request_pause(_):
    log.info(f"pause requested by {request.sid}")
    requester_nick = subscribers[request.sid].nick
    global current_state
    current_state = PAUSED
    emit(
        "log_message", {
            "data": f'Pause requested by "{requester_nick}"',
            "state": STATE_NAMES[current_state]
        }, namespace="/subscribe", broadcast=True, include_self=True)
    emit("pause", namespace="/publish", broadcast=True)


@socketio.on("resume", namespace='/subscribe')
def request_resume(_):
    log.info(f"resume requested by {request.sid}")
    requester_nick = subscribers[request.sid].nick
    global current_state
    current_state = PLAYING
    emit(
        "log_message", {
            "data": f'Resume requested by "{requester_nick}"',
            "state": STATE_NAMES[current_state]
        }, namespace="/subscribe", broadcast=True, include_self=True)
    emit("resume", namespace="/publish", broadcast=True)


@socketio.on("seek", namespace='/subscribe')
def request_seek(dst):
    log.info(f"seek requested to {dst} by {request.sid}")
    requester_nick = subscribers[request.sid].nick
    try:
        seek_dst = int(dst['seek'])
    except (KeyError, ValueError):
        emit("log_message", {
            "data": 'Invalid seek requested ({}). Must be in seconds.'.format(
                dst['seek'])}, namespace="/subscribe")
        return
    else:
        emit("log_message", {
            "data": 'Seek requested to {} by "{}"'.format(seek_dst,
                                                          requester_nick)},
             namespace="/subscribe", broadcast=True, include_self=True)
        emit("seek", {"seek": seek_dst}, namespace="/publish", broadcast=True)


@socketio.on("change nick", namespace='/subscribe')
def change_nick(msg):
    log.info("subscriber nick change requested")
    # log.info(request.event)

    old_nick = subscribers[request.sid].nick
    color = subscribers[request.sid].color
    try:
        new_nick = msg['new']
    except KeyError:
        emit("log_message", {"data": "obey the API! (missing key 'new')"})
        return
    if old_nick == new_nick:
        emit("log_message",
             {"data": f'Your nick is already "{new_nick}"'})
        return
    else:
        other_nicks = {z.nick for z in subscribers.values()}.union(
            {z.nick for z in publishers.values()})
        if new_nick in other_nicks:
            emit("log_message",
                 {"data": f"Nick {new_nick} already exists"})
            return

    subscribers[request.sid].nick = new_nick

    emit('nick change', {'new': new_nick, 'old': old_nick, "color": color,
                         'complete': clean_subscribers()}, broadcast=False)
    emit("update subscriptions",
         {'complete': clean_subscribers(), 'new': new_nick,
          'old': old_nick}, broadcast=True, include_self=False)


@socketio.on('broadcast message', namespace='/subscribe')
def broadcast_message(message):
    """A chat message to other subscribers"""
    log.info(f"Subscriber broadcasting: {message}")
    nick = subscribers[request.sid].nick
    color = subscribers[request.sid].color
    try:
        content = message['data']
    except KeyError:
        pass
    else:
        emit('log_message', {'data': content, 'nick': nick, 'color': color},
             broadcast=True, include_self=False)
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
        log.info(
            'subscriber {} just disconnected - total: {}'.format(
                request.sid, len(subscribers)))
        emit('update subscriptions',
             {'complete': clean_subscribers(), 'new': None,
              'old': old_nick}, broadcast=True)
