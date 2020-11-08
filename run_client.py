#!/usr/bin/env python3
import logging
import argparse
import asyncio
import sys
import subprocess

import socketio

from client.websocket import PublishNamespace
from client.vlc.playerctl import ForkingPlayerctlClient
from client.vlc.unixsocket import UnixSocketClient

log = logging.getLogger(__name__)
_version = (0, 0, 1)  # TODO: should be accessed from one place


def main():
    if sys.platform == "linux":
        clients = {
            "introspective": None,  # assign later because of dependencies
            "playerctl": ForkingPlayerctlClient,
            "unixsocket": UnixSocketClient
        }
        default_client = "introspective"

    elif sys.platform == "darwin":
        clients = {
            "unixsocket": UnixSocketClient
        }
        default_client = "unixsocket"

    elif sys.platform == "windows":
        print("windows not yet supported")
        loop = asyncio.ProactorEventLoop()  # for subprocesses on windows
        asyncio.set_event_loop(loop)
        return 1
    else:
        print(f"Platform '{sys.platform}' not supported")
        return 1

    def get_commit_id():
        # called on every launch, but that's ok for now
        return subprocess.run(["git", "describe", "--always"],
                              stdout=subprocess.PIPE,
                              timeout=0.5).stdout.decode('utf-8').strip()

    # argparse setup
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='datenight client')

    # optional arguments
    parser.add_argument('-v', action='count',
                        help="verbosity increases with each 'v' "
                             "| critical/error/warning/info/debug",
                        default=0)
    parser.add_argument('-s', '--server', type=str, default="http://localhost",
                        help="hostname to connect to")
    parser.add_argument('-p', '--port', default=None, type=int,
                        help="port to connect to (if unspecified, defaults to "
                             "80 for http:// and 443 for https://)")
    parser.add_argument('-c', '--client', default=default_client, type=str,
                        choices=clients.keys(), help="Choice of client to use")
    parser.add_argument('-a', '--alias', type=str, default=None,
                        help="Name by which this publisher will be known as")
    parser.add_argument('-o', '--offset', default=0, type=int,
                        help="Offset (+/- <seconds> if any), to apply on the "
                             "local file")
    parser.add_argument('-V', '--version', action='version',
                        version="%(prog)s v{} ({})".format(
                            '.'.join(map(str, _version)), get_commit_id()),
                        help="Show version and exit")

    args = parser.parse_args()
    if args.client not in clients:
        # fallback if the default_client is invalid
        print(f"Must choose a client (-c) from {clients.keys()}")
        return 1
    if args.client == "introspective":
        try:
            from client.vlc.introspective import IntrospectiveVLCClient
        except ValueError:
            print(
                "You don't have playerctl installed "
                "(needed for the playerctl client)\n"
                "Install it or use an alternative client with the -c flag")
            return 1
        else:
            clients['introspective'] = IntrospectiveVLCClient

        try:
            import gbulb
        except ImportError:
            print(
                "You don't have the gbulb module installed. Falling back to "
                "asyncio_glib which has an upstream issue preventing it from "
                "reporting status immediately (delaying async events)")
            try:
                import asyncio_glib
            except ImportError:
                print(
                    "You don't have the asyncio_glib module installed "
                    "(needed for the introspective client)\n"
                    "Install it or use an alternative client with the -c flag")
                return 1
            else:
                asyncio.set_event_loop_policy(
                    asyncio_glib.GLibEventLoopPolicy())
        else:
            gbulb.install()

    # logger setup
    level = max(10, 50 - (10 * args.v))
    print(f'Logging level is: {logging.getLevelName(level)}')
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s: %(levelname)s:\t%(message)s')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    logger = logging.getLogger('client')
    logger.setLevel(level)
    logger.addHandler(sh)

    if args.port is None:
        if args.server.startswith("https"):
            args.port = 443
        elif args.server.startswith("http"):
            args.port = 80

    return asyncio.run(start_loop(args, clients))


async def start_loop(args, clients):
    socket_io = socketio.AsyncClient(logger=False)

    host = f'{args.server}:{args.port}'
    try:
        await socket_io.connect(host, namespaces=['/publish'])
    except socketio.exceptions.ConnectionError:
        print(f"Fatal: Couldn't connect to {host}")
        return 1

    publish = PublishNamespace(namespace='/publish')
    socket_io.register_namespace(publish)

    client = clients[args.client](publish, args.offset)
    await publish.initialize_namespace(client, args.alias)

    try:
        await socket_io.wait()
    except ConnectionResetError:
        print("Aborting client...")
        return 1


if __name__ == '__main__':
    sys.exit(main())
