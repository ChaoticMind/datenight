### Datenight ###

Datenight aims to solve the problem of online sync'ing when multiple parties
are consuming the same media together over the internet.


### Client ###


#### Client dependencies ####

- On OSX and Linux:
	- Python3.5
	- SocketIO-client ([pypi](https://pypi.python.org/pypi/socketIO-client) - [github](https://github.com/invisibleroads/socketIO-client))
		- `pip install socketIO_client`
- On Linux:
	- playerctl ([AUR](https://aur.archlinux.org/packages/playerctl/) - [github](https://github.com/acrisci/playerctl)) if you want to use the introspective (recommended) or forking clients
	- gbulb ([pypi](https://pypi.python.org/pypi/gbulb) - [github](https://github.com/nathan-hoad/gbulb)) if you want to use the introspective client (recommended)
		- `pip install gbulb`


#### Client notes ####

- The only client supported so far is vlc
- Having two clients open is unsupported and results in undefined behavior
- The unixsocket client on OS X or linux requires a one-time configuration to VLC. On vlc 2.2.3, the instructions are as follows:
	1. Go to tools --> preferences (ctrl/cmd + P)
	2. Toggle "show settings" to "All" instead of "Simple" (bottom left corner)
	3. Under "Interface" --> "Main interfaces", tick "Remote control interface"
	4. Under "Interface" --> "Main interfaces" --> "RC", tick "Fake TTY" and type "/tmp/vlc.sock" as the "UNIX socket command input"
	5. Save and restart VLC


#### Running the client ####

The client can be run via the `./run_client.py` script. `-h` for help.


### Server ###


#### Server dependencies ####

- Python3
- Flask-SocketIO


#### Running the server ####

The server can be run via the `./run_server.py` script. `-h` for help.


### TODO ###

- resume countdown (in 3..2..1)
- save publishers as objects on datenight.js + only send relevant data from server
- migrate client to twisted/autobahn/sockjs
- support multiple rooms
- client for windows
- after "stability" is reached, split client/server into separate repos
