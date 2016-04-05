import asyncio
import argparse

from . import Server, Universe
from .net import h2

def main(args=None):
    parser = argparse.ArgumentParser(description='Run an SSP server')
    parser.add_argument('--bind', '-b', default='127.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8443)
    args = parser.parse_args(args)
    
    loop = asyncio.get_event_loop()
    universe = Universe()
    server = Server(loop, universe)
    
    server.start()
    coro = loop.create_server(h2.h2_protocol(server), args.bind, args.port, ssl=h2.create_ssl_context())
    h2_server = loop.run_until_complete(coro)

    print('Server running on {}'.format(h2_server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    h2_server.close()
    loop.run_until_complete(h2_server.wait_closed())

    server.stop()
    loop.run_until_complete(server.wait_finished())
    loop.close()

if __name__ == '__main__':
    main()
