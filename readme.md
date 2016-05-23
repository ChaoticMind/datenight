### Datenight ###

Datenight aims to solve the problem of online sync'ing when multiple parties
are consuming the same media together over the internet.


#### Client dependencies ####
  - Python3.5
  - SocketIO-client ([pypi](https://pypi.python.org/pypi/socketIO-client) - [github](https://github.com/invisibleroads/socketIO-client))
  - On Linux:
    - playerctl ([AUR](https://aur.archlinux.org/packages/playerctl/) - [github](https://github.com/acrisci/playerctl)) if you want to use the introspective (recommended) or forking clients
    - gbulb ([pypi](https://pypi.python.org/pypi/gbulb) - [github](https://github.com/nathan-hoad/gbulb)) if you want to use the introspective client (recommended)


### Client notes ###
	- The unixsocket client on OS X or linux requires a one-time configuration to VLC
	# TODO: write some instructions for the onetime config


#### Server dependencies ####
  - Python3
  - Flask-SocketIO


#### TODO ####
  - resume countdown (in 3..2..1)
  - make log div use html (update add_to_log() in util.js)
  - save publishers as objects on datenight.js + only send relevant data from server
  - migrate client to twisted/autobahn/sockjs
  - support multiple rooms
  - client for windows
  - after "stability" is reached, split client/server into separate repos
