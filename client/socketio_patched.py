import logging

from socketIO_client import SocketIO
from socketIO_client.exceptions import ConnectionError, TimeoutError, PacketError


log = logging.getLogger(__name__)


class SocketIOPatched(SocketIO):
	"""Workaround/fix for
	https://github.com/invisibleroads/socketIO-client/issues/117
	http://stackoverflow.com/questions/37058119/python-and-socket-io-app-hangs-after-connection

	"""
	def _should_stop_waiting(self, for_connect=False, for_callbacks=False):
		if for_connect:
			for namespace in self._namespace_by_path.values():
				is_namespace_connected = getattr(namespace, '_connected', False)
				if not is_namespace_connected and namespace.path:  # added namespace.path
					return False
			return True
		if for_callbacks and not self._has_ack_callback:
			return True
		return super(SocketIO, self)._should_stop_waiting()

	# Additional patch for set_timeout()
	def wait(self, seconds=None, **kw):
		'Wait in a loop and react to events as defined in the namespaces'
		# Use ping/pong to unblock recv for polling transport
		self._heartbeat_thread.hurry()
		# Use timeout to unblock recv for websocket transport
		# self._transport.set_timeout(seconds=1)
		self._transport.set_timeout(seconds=seconds)  # patch here
		# Listen
		warning_screen = self._yield_warning_screen(seconds)
		for elapsed_time in warning_screen:
			if self._should_stop_waiting(**kw):
				break
			try:
				try:
					self._process_packets()
				except TimeoutError:
					pass
			except ConnectionError as e:
				self._opened = False
				try:
					warning = Exception('[connection error] %s' % e)
					warning_screen.throw(warning)
				except StopIteration:
					self._warn(warning)
				try:
					namespace = self.get_namespace()
					namespace.on_disconnect()
				except PacketError:
					pass
		self._heartbeat_thread.relax()
		self._transport.set_timeout()
