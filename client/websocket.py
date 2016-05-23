import logging

from socketIO_client import BaseNamespace

log = logging.getLogger(__name__)


class PublishNamespace(BaseNamespace):
	def update_alias(self, new_alias):
		"""would have been done in on_connect() if it were possible to send alias to __init__"""
		log.info("Requesting alias update to {}...".format(new_alias))
		self.emit('set nick', {"new": new_alias})

	def initialize_namespace(self, client):
		self.client = client
		log.info("Requesting ua update to {}...".format(client.ua))
		self.emit('set ua', {"user_agent": client.ua})
		# self._initialized = True

	def on_latency_ping(self, msg):
		log.debug("Received latency_ping...")
		self.emit('latency_pong', msg)

	def on_pause(self, msg):
		log.info("Received pause request")
		self.client.pause()

	def on_resume(self, msg):
		log.info("Received resume request")
		self.client.resume()

	def on_seek(self, msg):
		log.info("Received seek request to {}".format(msg))
		try:
			seek_dst = int(msg['seek'])
		except (KeyError, ValueError):
			log.info("Invalid seek destination, ignoring...")
		else:
			self.client.seek(seek_dst)

	def on_log_message(self, msg):
		"""Server asked us to inform the user of a msg"""
		try:
			nick = msg['nick']
		except KeyError:
			log.info("remote message: {}".format(msg['data']))
		else:
			log.info("remote message: {}: {}".format(nick, msg['data']))

		try:
			if (msg['fatal']):
				log.info("Fatal error received, disconnecting...")
				self.disconnect()
		except KeyError:
			pass

	def on_error(self, msg):
		log.error("socketio error: {}".format(msg))

	def wait(self, *args, **kwargs):
		self._io.wait(*args, **kwargs)

	def regular_peek(self, loop):
		"""Unfortunately, we couldn't use nonblocking sockets in a sane way.
		Socketio-client doesn't seem to provide it.

		We're regularily blocking for small periods of time instead.
		We can modify these values to find a good balance between responsiveness and CPU usage

		"""
		# log.debug("Peeking")
		self.wait(seconds=0.025)
		# log.debug("Peeked")
		loop.call_later(0.01, self.regular_peek, loop)
		return True
