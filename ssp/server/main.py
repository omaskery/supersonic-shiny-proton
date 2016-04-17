import asyncio
import argparse
import logging
import sys

import ssp.logging
import ssp.scripting.emulator

from . import Server, Universe
from .net import h2

logger = logging.getLogger(__name__)

def main(args=None):
    parser = argparse.ArgumentParser(description='Run an SSP server')
    parser.add_argument('--bind', '-b', default='127.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8443)
    parser.add_argument('--network-logging')
    args = parser.parse_args(args)
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(handler)
    rootLogger.setLevel(logging.INFO)

    if args.network_logging is not None:
        ssp.logging.start_network_logging(args.network_logging)
        rootLogger.setLevel(logging.DEBUG)
        
    loop = asyncio.get_event_loop()
    universe = Universe()
    server = Server(loop, universe)

    logger.info('Starting server')

    server.start()
    coro = loop.create_server(h2.h2_protocol(loop, server), args.bind, args.port, ssl=h2.create_ssl_context())
    h2_server = loop.run_until_complete(coro)

    logger.info('Server running on {}'.format(h2_server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    logger.info('Stopping server')

    h2_server.close()
    loop.run_until_complete(h2_server.wait_closed())

    server.stop()
    loop.run_until_complete(server.wait_finished())
    loop.close()

if __name__ == '__main__':
    main()
