### Datenight ###

Datenight aims to solve the problem of online sync'ing when multiple parties
are consuming the same media together over the internet.


#### Client dependencies ####
  - SocketIO-client ([pypi](https://pypi.python.org/pypi/socketIO-client) - [github](https://github.com/invisibleroads/socketIO-client))
  - On Linux: playerctl ([AUR](https://aur.archlinux.org/packages/playerctl/) - [github](https://github.com/acrisci/playerctl)) and gbulb ([pypi](https://pypi.python.org/pypi/gbulb) - [github](https://github.com/nathan-hoad/gbulb))


#### Server dependencies ####
  - Flask-SocketIO


#### TODO ####
  - client for osx
  - resume countdown (in 3..2..1)
  - make log div use html (update add_to_log() in util.js)
  - save publishers as objects on datenight.js + only send relevant data from server
  - migrate client to twisted/autobahn/sockjs
  - support multiple rooms
  - client for windows
  - after "stability" is reached, split client/server into separate repos
