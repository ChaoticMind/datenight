import logging

from gi.repository import GLib
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

	def regular_peek(self):
		# log.info("Peeking")
		self.wait(seconds=0.025)
		# log.info("Peeked")
		# GLib.idle_add(self.regular_peek)
		# GLib.timeout_add(500, self.regular_peek)
		return True


class DatenightWS():
	"""This class is now superflous, remove it"""
	def __init__(self, client):
		logging.getLogger('').setLevel(logging.DEBUG)

		socket_io = SocketIOPatched('localhost', 5000)
		log.info("Connected...")
		publish = socket_io.define(PublishNamespace, '/publish')
		publish.client = client
		client.sock = publish
		log.info("Connected to /publish")
		# socket_io.wait(seconds=0)
		# GLib.idle_add(publish.regular_peek)
		GLib.timeout_add(10, publish.regular_peek)
