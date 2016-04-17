import aioh2
import ssl
import logging
import json
import collections

import sys

# For Auth
import ssp.server.net.h2
h2 = ssp.server.net.h2

def _make_method_fn(method):
    async def method_fn(self, *a, **kw):
        return await self.request(method, *a, **kw)
    return method_fn

class Response(object):
    pass

class Client(object):
    logger = logging.getLogger(__name__)
    
    METHODS = {
        'get': 'GET',
        'post': 'POST',
    }
    
    def __init__(self, loop=None):
        self.loop = loop

    def create_ssl_context(self):
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.set_ciphers("ECDHE+AESGCM")
        ssl_context.set_alpn_protocols(["h2"])
        return ssl_context

    async def connect(self, host, port):
        self.logger.info('Connecting to {}:{}'.format(host, port))
        self.client = await aioh2.open_connection(host, port, loop=self.loop, ssl=self.create_ssl_context())
        self.logger.debug('Connected')

    for k,v in METHODS.items():
        locals()[k] = _make_method_fn(v)

    async def request(self, method, path, payload=None, auth=None):
        self.logger.info('{} {}'.format(method, path))
        headers = {
            ':method': method,
            ':path': path,
        }

        if auth is not None:
            h2.sign_machine_auth(headers, *auth)

        special_headers = []
        normal_headers = []
        for k, v in headers.items():
            if k.startswith(':'):
                special_headers.append((k, v))
            else:
                normal_headers.append((k, v))
        
        stream_id = await self.client.start_request(special_headers + normal_headers)

        self.logger.debug('Started')
        await self.client.send_data(stream_id, payload or b'', end_stream=True)
        self.logger.debug('Sent data')
        headers = await self.client.recv_response(stream_id)
        self.logger.debug('Headers: {}'.format(headers))
        body = await self.client.read_stream(stream_id, -1)
        self.logger.debug('Body: {}'.format(body))
        
        headers = collections.OrderedDict(headers)
        json_body = None
        
        if headers.get('content-type', '').lower() == 'application/json':
            body_str = body.decode('utf-8').strip()
            if len(body_str) > 0:
                json_body = json.loads(body.decode('utf-8'))

        resp = Response()
        resp.headers = headers
        resp.body = body
        resp.json = json_body
        return resp
        

