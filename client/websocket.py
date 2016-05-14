import logging

from socketIO_client import BaseNamespace

from client.socketio_patched import SocketIOPatched

log = logging.getLogger(__name__)


class PublishNamespace(BaseNamespace):
	def on_latency_ping(self, msg):
		log.info("Received latency_ping...")
		self.emit('latency_pong', msg)

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


class DatenightWS():
	def __init__(self):
		logging.getLogger('').setLevel(logging.DEBUG)

		# self.socket_io = SocketIO('localhost', 5000)
		self.socket_io = SocketIOPatched('localhost', 5000)
		log.info("Connected...")
		self.publish = self.socket_io.define(PublishNamespace, '/publish')
		log.info("Connected to /publish")
		# self.socket_io.wait(seconds=0)
		self.socket_io.wait(seconds=0.05)
		# self.disconnect()

	def emit(self, *args, **kwargs):
		self.publish.emit(*args, **kwargs)

	def disconnect(self):
		log.info("Disconnecting...")
		self.socket_io.disconnect()
		log.info("Disconnected...")
