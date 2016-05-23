import logging
import sys
import os
import urllib.request
import asyncio
from functools import partial

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # TODO: should be in __init__()


class UnixSocketClient():
	"""Currently specific to vlc, but can be generalized similar to ForkingClient"""
	REPORT_PERIOD = 1
	ua = "{}_unixsocket_{}".format(sys.platform, '.'.join(map(str, _version)))

	class UnixProtocol(asyncio.Protocol):
		def __init__(self, client, *args, **kwargs):
			self._client = client

			self._pause_strings = ["status change: ( pause state: 3 ): Pause"]
			self._play_strings = ["status change: ( play state: 2 ): Play", "status change: ( play state: 3 )"]
			# think I saw this once as a play_string, but can't reproduce: "status change: ( pause state: 4 )"
			self._stop_strings = ["status change: ( play state: 4 ): End", "status change: ( stop state: 0 )", "status change: ( pause state: 4 ): End"]

			self._state_str = {
				0: "Paused",
				1: "Playing",
				2: "Stopped"
			}
			self._state = 0
			self._title = ""
			self._position = 0
			self._length = 0

			super().__init__(*args, **kwargs)

		def connection_made(self, transport):
			self._transport = transport
			log.debug("Connection to unixsocket established")

		def send_data(self, data):
			log.debug("Writing to the unix socket: {}".format(data.encode()))
			self._transport.write(data.encode())

		@staticmethod
		def _droppable_strings(x):
			if x.startswith('status change:'):
				# used when state is updated
				return True
			elif x.startswith('seek: returned '):
				# used when seeking and immediately updating/probing
				return True
			elif x.startswith('pause: returned'):
				# used when seeking from a paused state
				return True
			else:
				return False

		def data_received(self, data):
			decoded = data.decode('utf-8').strip()
			log.debug('Data received on the unix socket: {}'.format(decoded))
			emit = False

			lines = decoded.split('\r\n')
			one_shots = [l for l in lines if l.startswith('status change:')]
			lines = [l for l in lines if not self._droppable_strings(l)]  # filter
			for x in one_shots:
				if x.startswith("status change: ( new input:"):
					# VLC possible bug: doesn't emit new input or "play" to the socket
					# unless the socket is written to by something else first? - strange.
					skip = len("status change: ( new input:")
					fname = os.path.basename(x[skip:])
					self._title = urllib.request.unquote(fname)
					self.emit_to_sock(show=True)
				elif x in self._pause_strings:
					self._state = 0
					log.info("Reporting pause state")
					self.emit_to_sock(show=True)
				elif x in self._play_strings:
					self._state = 1
					log.info("Reporting playing state")
					self.emit_to_sock(show=True)
				elif x in self._stop_strings:
					self._state = 2
					self._position = 0
					self._length = 0
					self._title = ""
					log.info("Reporting stopped state")
					self.emit_to_sock(show=True)
				elif x.startswith("status change: ( time: "):
					try:
						skip = len("status change: ( time: ")
						self._position = int(x[skip:-3])
						self.emit_to_sock(show=False)
					except ValueError:
						pass
				else:  # other line starting with "status change" -- unsupported
					# e.g. volume changed
					pass

			log.debug("received {} lines".format(len(lines)))
			if len(lines) == 3:
				position, title, length = lines
				try:
					position, length = int(position), int(length)
				except ValueError:
					return
				else:
					if length != self._length or title != self._title:
						emit, show = True, True
					elif position != self._position:
						emit, show = True, False
					else:
						emit = False
					self._title, self._position, self._length = title, position, length

			if emit:
				self.emit_to_sock(show)

		def emit_to_sock(self, show):
				# could reset the periodic probe here, but it's not really necessary
				# introspective client behavior is to reset it atm
				log.debug("Reporting state")
				self._client.websock.emit("update state", {
					"title": self._title,
					"status": self._state_str[self._state],
					"position": "{}/{}".format(self._position, self._length),
					"show": show})

		def connection_lost(self, e):
			log.debug('The unix socket is now closed, cancelling periodic probe')
			self._client.handler.cancel()
			asyncio.ensure_future(self._client.open_unixsock())

	def __init__(self, websock):
		# self.reader = None
		# self.writer = None
		self.protocol = None
		self.websock = websock

		asyncio.ensure_future(self.open_unixsock())

	async def open_unixsock(self):
		loop = asyncio.get_event_loop()
		expected_path = "/tmp/vlc.sock"
		try:
			ProtocolWithParam = partial(UnixSocketClient.UnixProtocol, self)
			transport, self.protocol = await loop.create_unix_connection(ProtocolWithParam, path=expected_path)
			# self.reader, self.writer = await asyncio.open_unix_connection(expected_path)
		except FileNotFoundError:
			log.critical('no unix socket found at {} - is vlc open?'.format(expected_path))
			loop = asyncio.get_event_loop()
			delayed_ensure_future = partial(asyncio.ensure_future, self.open_unixsock())
			loop.call_later(self.REPORT_PERIOD, delayed_ensure_future)
		else:
			loop = asyncio.get_event_loop()
			self.handler = loop.call_soon(self._periodic_probe)

	# actions requested
	def pause(self):
		log.info("Received request to pause")
		log.info("Current state is: {}".format(self.protocol._state))
		# 0: "Paused",
		# 1: "Playing",
		# 2: "Stopped"
		if self.protocol._state == 1:
			self.protocol.send_data("pause\n")

	def resume(self):
		log.info("Received request to resume")
		log.info("Current state is: {}".format(self.protocol._state))
		if self.protocol._state == 0:
			self.protocol.send_data("pause\n")  # means "resume"
		elif self.protocol._state == 2:
			# 'play' only means start for the vlc rc client
			self.protocol.send_data("play\n")

	def seek(self, seek_dst):
		log.info("Received request to seek to {}".format(seek_dst))
		if self.protocol._state == 0:
			self.protocol.send_data("pause\n")
			self.protocol.send_data("seek {}\n".format(seek_dst))
			self.protocol.send_data("pause\n")
		else:
			self.protocol.send_data("seek {}\n".format(seek_dst))
			self._periodic_probe()

	def _periodic_probe(self):
		self.handler.cancel()
		log.debug("Probing...")
		self.protocol.send_data("get_time\n")
		self.protocol.send_data("get_title\n")
		self.protocol.send_data("get_length\n")

		loop = asyncio.get_event_loop()
		self.handler = loop.call_later(self.REPORT_PERIOD, self._periodic_probe)
