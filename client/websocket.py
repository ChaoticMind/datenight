import logging

from socketio import AsyncClientNamespace

log = logging.getLogger(__name__)


class PublishNamespace(AsyncClientNamespace):
    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    async def update_alias(self, new_alias):
        # would have been done in on_connect() if it were possible to send
        # alias to __init__
        log.info("Requesting alias update to {}...".format(new_alias))
        await self.emit('set nick', {"new": new_alias})

    async def initialize_namespace(self, client, alias=None):
        self.datenight_client = client
        log.info("Requesting ua update to {}...".format(client.ua))
        await self.emit('set ua', {"user_agent": client.ua})
        if alias:
            await self.update_alias(alias)
        # self._initialized = True

    async def on_latency_ping(self, msg):
        log.debug("Received latency_ping...")
        await self.emit('latency_pong', msg)

    def on_pause(self):
        log.info("Received pause request")
        self.datenight_client.pause()

    def on_resume(self):
        log.info("Received resume request")
        self.datenight_client.resume()

    def on_seek(self, msg):
        log.info("Received seek request to {}".format(msg))
        try:
            seek_dst = int(msg['seek'])
        except (KeyError, ValueError):
            log.info("Invalid seek destination, ignoring...")
        else:
            self.datenight_client.seek(seek_dst)

    async def on_log_message(self, msg):
        """Server asked us to inform the user of a msg"""
        try:
            nick = msg['nick']
        except KeyError:
            log.info("remote message: {}".format(msg['data']))
        else:
            log.info("remote message: {}: {}".format(nick, msg['data']))

        try:
            if msg['fatal']:
                log.info("Fatal error received, disconnecting...")
                await self.disconnect()
        except KeyError:
            pass

    def on_error(self, msg):
        log.error("socketio error: {}".format(msg))
