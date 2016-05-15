import logging
import asyncio

from socketIO_client import BaseNamespace

from client.socketio_patched import SocketIOPatched

log = logging.getLogger(__name__)


class PublishNamespace(BaseNamespace):
	def on_latency_ping(self, msg):
		log.info("Received latency_ping...")
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
		try:
			nick = msg['nick']
		except KeyError:
			log.info("{}".format(msg['data']))
		else:
			log.info("{}: {}".format(nick, msg['data']))

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
		# log.debug("Peeking")
		self.wait(seconds=0.025)
		# log.debug("Peeked")
		loop.call_later(0.01, self.regular_peek, loop)
		return True


class DatenightWS():
	"""This class is now superflous, remove it"""
	def __init__(self, client):
		logging.getLogger('').setLevel(logging.DEBUG)

		socket_io = SocketIOPatched('localhost', port=5000)
		log.info("Connected...")
		publish = socket_io.define(PublishNamespace, '/publish')
		publish.client = client
		client.sock = publish
		log.info("Connected to /publish")

		loop = asyncio.get_event_loop()
		loop.call_soon(publish.regular_peek, loop)
