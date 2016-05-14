import logging

from flask import Flask
from flask.ext.socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
log = logging.getLogger(__name__)

# globals
subscribers = {}
publishers = {}

(PLAYING, PAUSED) = (0, 1)
STATE_NAMES = ['Playing', 'Paused']
current_state = PAUSED

subscribers_nick_presets = [
	"macaw", "rhino", "addax", "gharial", "vaquita", "bonobo", "dhole", "panda",
	"red_wolf", "saiga", "hippo", "takhi", "fossa", "sangai",
	"dugong", "yak", "takin", "dingo", "gaur",
]

from server.views import general, publisher, subscriber  # noqa
