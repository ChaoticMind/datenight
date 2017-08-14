import logging

from server import publishers, subscribers

log = logging.getLogger(__name__)


def clean_publishers():
    # index by nick instead of request.sid (which is private info)
    return {p.nick: p.dict_repr() for p in publishers.values()}


def clean_subscribers():
    # index by nick instead of request.sid (which is private info)
    return {s.nick: s.dict_repr() for s in subscribers.values()}
