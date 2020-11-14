import logging
from enum import Enum

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
log = logging.getLogger(__name__)


class PlayerState(Enum):
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"


# globals
subscribers = {}
publishers = {}
current_state = PlayerState.PAUSED

# presets
subscribers_nick_presets = [
    "macaw", "rhino", "addax", "gharial", "vaquita", "bonobo", "dhole",
    "panda", "red_wolf", "saiga", "hippo", "takhi", "fossa", "sangai",
    "dugong", "yak", "takin", "dingo", "gaur",
]

subscribers_color_presets = [  # valid css colors
    "tomato", "tan", "springgreen", "skyblue", "slateblue", "sienna", "salmon",
    "palevioletred", "orangered", "mediumseagreen", "magenta",
    "lightseagreen", "firebrick", "blueviolet", "teal",
    "green",
]

from server.views import general, publisher, subscriber  # noqa
