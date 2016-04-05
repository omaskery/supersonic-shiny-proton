import asyncio
import argparse
from . import Client

def main(args=None):
    parser = argparse.ArgumentParser(description='Do things to an SSP server')
    parser.add_argument('--host',  default='127.0.0.1')
    parser.add_argument('--port', '-p', type=int, default=8443)
    args = parser.parse_args(args)
    
    loop = asyncio.get_event_loop()
    client = Client(loop)

    async def run():
        await client.connect(args.host, args.port)
        print(await client.get('/'))
    
    loop.run_until_complete(run())
    loop.close()

if __name__ == '__main__':
    main()
