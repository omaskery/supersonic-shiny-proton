import asyncio
import argparse
import logging
import sys

import ssp.logging

from . import Client

def main(args=None):
    parser = argparse.ArgumentParser(description='Do things to an SSP server')
    parser.add_argument('--host',  default='127.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8443)
    parser.add_argument('programs', nargs='+', help='Program files to run')
    parser.add_argument('--network-logging')
    args = parser.parse_args(args)

    # Setup logging
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.WARNING)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(handler)
    rootLogger.setLevel(logging.WARNING)

    if args.network_logging is not None:
        ssp.logging.start_network_logging(args.network_logging)
        rootLogger.setLevel(logging.DEBUG)

    
    loop = asyncio.get_event_loop()
    client = Client(loop)

    async def run():
        await client.connect(args.host, args.port)
        resp = await client.post('/machines/')
        auth = (resp.json['id'], resp.json['secret'])

        for path in args.programs:
            with open(path, 'rb') as f:
                contents = f.read()
                resp = await client.post('/machines/{}/start-process'.format(auth[0]), contents, auth=auth)
                print(resp.body)
    
    loop.run_until_complete(run())
    loop.close()

if __name__ == '__main__':
    main()
