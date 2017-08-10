import logging

from server import publishers

log = logging.getLogger(__name__)


def clean_publishers():
    # index by nick instead of request.sid (which is private info)
    return {v.nick: v.dict_repr() for v in publishers.values()}
