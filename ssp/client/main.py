import asyncio
import argparse
import errno
import logging
import os
import sys
import yaml
from appdirs import AppDirs

import ssp.logging

from . import Client

def ensure_path(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def load_config(client, config_path):
    client.config = {}
    
    if not os.path.isfile(config_path):
        return
    
    with open(config_path, 'rb') as f:
        config = yaml.load(f.read().decode('utf-8'))
        f.close()

        if isinstance(config, dict):
            client.config = config

def save_config(client, config_path):
    with open(config_path, 'wb') as f:
        f.write(yaml.dump(client.config).encode('utf-8'))
        f.close()

def main(args=None):
    parser = argparse.ArgumentParser(description='Do things to an SSP server')
    parser.add_argument('--host',  default='127.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8443)
    parser.add_argument('--network-logging', help='Address to send network logging to')
    parser.add_argument('--create-machine', action='store_true')
    parser.add_argument('--start-program', action='append', default=[], help='Start a program.')
    parser.add_argument('--send-data', nargs=2, action='append', default=[], help='Send some data.')
    parser.add_argument('--send-file', nargs=2, action='append', default=[], help='Send some data.')
    args = parser.parse_args(args)

    appdirs = AppDirs('ssp', 'omaskery')
    ensure_path(appdirs.user_data_dir)
    config_path = os.path.join(appdirs.user_data_dir, 'config.yaml')

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
    load_config(client, config_path)

    async def run():
        await client.connect(args.host, args.port)

        if args.create_machine:
            resp = await client.post('/machines/')
            client.config['auth'] = [resp.json['id'], resp.json['secret']]
            save_config(client, config_path)

        auth = client.config.get('auth')
        if auth is not None:
            for path in args.start_program:
                with open(path, 'rb') as f:
                    contents = f.read()
                    await client.post('/machines/{}/start-process'.format(auth[0]), contents, auth=auth)
                    
            for (target, contents) in args.send_data:
                contents = contents.encode('utf-8')
                resp = await client.post('/machines/{}/send/{}'.format(auth[0], target), contents, auth=auth)
                print(resp)

            for (target, path) in args.send_file:
                with open(path, 'rb') as f:
                    contents = f.read()
                    print(target, contents)
                    resp = await client.post('/machines/{}/send/{}'.format(auth[0], target), contents, auth=auth)
                    print(resp)
                    
    loop.run_until_complete(run())
    loop.close()

if __name__ == '__main__':
    main()
