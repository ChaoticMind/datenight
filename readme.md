## Datenight ##

Datenight aims to solve the problem of sync'ing when multiple parties are co-consuming the same media.


### Client ###


#### Client dependencies ####

- On macOS and Linux (via unixsocket):
	- Python3.8
	- SocketIO-client ([pypi](https://pypi.python.org/pypi/socketIO-client) - [github](https://github.com/invisibleroads/socketIO-client))
		- `pip install socketIO_client`
- On Linux:
	- playerctl ([Arch](https://www.archlinux.org/packages/community/x86_64/playerctl/) - [github](https://github.com/acrisci/playerctl)) if you want to use the introspective (recommended) or forking clients

	Additionally, for the introspective client (recommended):
	- PyGObject ([pypi](https://pypi.org/project/PyGObject/))
		- `pip install PyGObject`
	- GObject Introspection ([upstream](https://wiki.gnome.org/Projects/GObjectIntrospection))
		- `sudo pacman -S gobject-introspection`

	And one of the following two packages:
	- gbulb ([github](https://github.com/nathan-hoad/gbulb) - [AUR](https://aur.archlinux.org/packages/python-gbulb/)) Unmaintained upstream, use AUR to get py3.8 patch (recommended)
	- asyncio-glib ([pypi](https://pypi.python.org/pypi/asyncio-glib) - [github](https://github.com/jhenstridge/asyncio-glib) - [AUR](https://aur.archlinux.org/packages/python-asyncio-glib/)) This works as a fallback from gbulb, but doesn't immediately report status due to an upstream bug
		- `pip install asyncio-glib`

Dependencies can be installed via `pip install -r client_requirements`


#### Client notes ####

- The only client supported so far is vlc
- Having two clients open is unsupported and results in undefined behavior
- The unixsocket client on macOS or linux requires a one-time configuration to VLC. On vlc 2.2.3, the instructions are as follows:
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

Dependencies can be installed via `pip install -r server_requirements`


#### Running the server ####

The server can be run via the `./run_server.py` script. `-h` for help.


### TODO ###

- resume countdown (in 3..2..1)
- save publishers as objects on datenight.js + only send relevant data from server
- migrate client to twisted/autobahn/sockjs
- support multiple rooms
- client for windows
- after "stability" is reached, split client/server into separate repos
