import logging
import random
import time
import json

import eventlet
from flask import request
from flask_socketio import emit, disconnect

from server import socketio, publishers, subscribers
from server import PlayerState
from server.helpers import clean_publishers
from . import SyncSuggestion

log = logging.getLogger(__name__)


class Publisher:
    PING_DELAY = 5
    TIMEOUT_THRESHOLD = 12

    def __init__(self, sid, nick):
        self.__sid = sid
        self.ua = "unknown"
        self.nick = nick
        self.latency = -1
        self.status = PlayerState.UNKNOWN.value
        self.position = -1
        self.length = -1
        self.title = ""
        self.__ping_token = None
        self.__ping_ts = None
        self.__heartbeat = eventlet.greenthread.spawn_n(self.__ping)
        self.__timeout = eventlet.greenthread.spawn_after(
            self.TIMEOUT_THRESHOLD, self.__process_timeout)

    def __ping(self):
        log.debug(f"{self.__sid}: ping request")
        self.__ping_token = random.randint(1, 10000000)
        self.__ping_ts = time.time()
        socketio.emit('latency_ping', {"token": self.__ping_token},
                      namespace='/publish', room=self.__sid)
        self.__heartbeat = eventlet.greenthread.spawn_after(self.PING_DELAY,
                                                            self.__ping)

    def __process_timeout(self):
        log.info(
            "{}: no ping reply in {} seconds, setting latency to -1".format(
                self.__sid, self.TIMEOUT_THRESHOLD))
        self.latency = -1
        self.__timeout = eventlet.greenthread.spawn_after(
            self.TIMEOUT_THRESHOLD, self.__process_timeout)
        socketio.emit('update publishers',
                      {'data': clean_publishers(), 'update': self.nick,
                       'show': False}, namespace='/subscribe', broadcast=True)

    def pong(self, token):
        log.debug(f"{self.__sid}: pong received")
        if not self.__ping_token == token:
            log.warning(f"{self.__sid}: Invalid token, ignoring...")
            return
        self.latency = round(time.time() - self.__ping_ts, 3)
        socketio.emit('update publishers',
                      {'data': clean_publishers(), 'update': self.nick,
                       'show': False}, namespace='/subscribe', broadcast=True)

        # reset timeout
        self.__timeout.cancel()
        self.__timeout = eventlet.greenthread.spawn_after(
            self.TIMEOUT_THRESHOLD, self.__process_timeout)

    def dict_repr(self):
        """Don't expose private data, this is sent over the wire"""
        return {
            'status': self.status,
            'position': f'{self.position}/{self.length}',
            'latency': self.latency,
            'title': self.title,
            'ua': self.ua,
        }

    def remove_timeouts(self):
        log.info(f"Removing timers from {self.__sid}")
        self.__heartbeat.cancel()
        self.__timeout.cancel()

    def __repr__(self):
        return json.dumps(self.dict_repr())

    def __del__(self):
        self.remove_timeouts()


# publish
@socketio.on('connect', namespace='/publish')
def connect_publisher():
    log.info(f"Connecting publisher {request.sid}")
    other_publisher_nicks = {z.nick for z in publishers.values()}
    other_nicks = other_publisher_nicks.union(
        {z.nick for z in subscribers.values()})

    if request.sid in publishers:
        raise RuntimeError(f"{request.sid} (publisher) Connected twice.")
    for i in range(10):
        x = str(random.randint(1, 10000))
        if x not in other_nicks:
            publishers[request.sid] = Publisher(sid=request.sid, nick=x)
            other_publisher_nicks.add(x)
            other_nicks.add(x)
            break
    else:
        log.info("Couldn't assign a nick, disconnecting the publisher...")
        emit("log_message",
             {"data": "Failed to assign you a nick", "fatal": True})
        return

    log.info(f"A publisher just connected (id={request.sid}, nick={x})"
             f" - total publishers: {len(publishers)}")
    emit('update publishers',
         {'data': clean_publishers(), 'new': x, 'old': None},
         namespace='/subscribe', broadcast=True)
    return True


@socketio.on('update state', namespace='/publish')
def message_trigger(message):
    log.info(f"Publisher state updated: {message}")
    nick = publishers[request.sid].nick
    # TODO: accept partial updates
    try:
        status = message['status']
        title = message['title']
        position = message['position']
        length = message['length']
        show = message.get('show', False)
        suggest_sync = message.get('suggest_sync', None)
    except KeyError as e:
        msg = f"Received missing data: {e}"
        log.error(msg)
        emit('log_message', {'data': msg}, namespace='/publish',
             broadcast=False)
        return False
    else:
        try:
            publishers[request.sid].status = PlayerState(status).value
        except ValueError:
            msg = f"Received bad state: {status}"
            log.error(msg)
            emit('log_message', {'data': msg})
            publishers[request.sid].status = PlayerState.UNKNOWN.value
            return False
        else:
            publishers[request.sid].title = title
            publishers[request.sid].position = position
            publishers[request.sid].length = length

        emit('update publishers',
             {'data': clean_publishers(), 'update': nick, 'show': show},
             namespace='/subscribe', broadcast=True)

        if suggest_sync:
            broadcast_sync_suggestion(
                suggest_sync, PlayerState(status), position)


def broadcast_sync_suggestion(
        suggest_sync: bool, status: PlayerState, position: int):
    requester_nick = publishers[request.sid].nick

    if suggest_sync == SyncSuggestion.STATE.value:
        global current_state
        request_str = "Pause"  # default/catch-all
        emit_str = "pause"

        if status == PlayerState.PLAYING:
            current_state = PlayerState.PLAYING
            request_str = "Resume"
            emit_str = "resume"
        if status == PlayerState.PAUSED:
            current_state = PlayerState.PAUSED
            request_str = "Pause"
            emit_str = "pause"

        socketio.emit(
            "log_message", {
                "data": f'{request_str} requested by "{requester_nick}"',
                "state": current_state.value
            },
            namespace="/subscribe")
        emit(emit_str, {'explicit': False}, namespace="/publish",
             broadcast=True, include_self=False)

    elif suggest_sync == SyncSuggestion.SEEK.value:
        socketio.emit(
            "log_message", {
                "data": f'Seek requested by "{requester_nick}"',
            },
            namespace="/subscribe")
        emit("seek", {"seek": position, "explicit": False}, namespace="/publish",
             broadcast=True, include_self=False)

    else:
        msg = f"Received bad suggest_sync: {suggest_sync}"
        log.error(msg)
        emit('log_message', {'data': msg})
        return False


@socketio.on('latency_pong', namespace='/publish')
def ping(message):
    try:
        publishers[request.sid].pong(message['token'])
    except KeyError:
        emit("log_message", {"data": "Received bad pong", "fatal": True})


@socketio.on("set nick", namespace='/publish')
def update_nick(msg):
    log.info("publisher nick change requested")

    old_nick = publishers[request.sid].nick
    try:
        new_nick = msg['new']
    except KeyError:
        emit("log_message", {"data": "obey the API! (missing key 'new')"})
        return
    if old_nick == new_nick:
        emit("log_message",
             {"data": f"Your nick is already {new_nick}"})
        return
    else:
        subscribers_nicks = {z.nick for z in subscribers.values()}
        other_nicks = subscribers_nicks.union(
            {z.nick for z in publishers.values()})
        if new_nick in other_nicks:
            emit("log_message",
                 {"data": f"Nick {new_nick} already exists"})
            return

    publishers[request.sid].nick = new_nick

    emit('log_message', {'data': f"nick updated to {new_nick}"},
         broadcast=False)
    emit('update publishers',
         {'data': clean_publishers(), 'new': new_nick, 'old': old_nick},
         namespace='/subscribe', broadcast=True)


@socketio.on("set ua", namespace='/publish')
def set_ua(msg):
    log.info("publisher ua change requested")

    try:
        ua = msg['user_agent']
    except KeyError:
        emit("log_message",
             {"data": "obey the API! (missing key 'user_agent')"})
        return

    publishers[request.sid].ua = ua
    nick = publishers[request.sid].nick

    emit('log_message', {'data': f"ua set to {ua}"}, broadcast=False)
    emit('update publishers',
         {'data': clean_publishers(), 'update': nick, 'show': False},
         namespace='/subscribe', broadcast=True)


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
        log.info(f'publisher {request.sid} just disconnected without a '
                 f'nick ever been assigned - total: {len(publishers)}')
    else:
        log.info(
            'publisher {} just disconnected - total: {}'.format(
                request.sid, len(publishers)))
        emit('update publishers',
             {'data': clean_publishers(), 'new': None, 'old': old_nick},
             namespace='/subscribe', broadcast=True)
