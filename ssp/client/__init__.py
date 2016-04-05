import aioh2
import ssl
import logging

def _make_method_fn(method):
    async def method_fn(self, path, payload=None):
        return await self.request(method, path, payload)
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

    async def request(self, method, path, payload=None):
        self.logger.info('{} {}'.format(method, path))
        stream_id = await self.client.start_request({
            ':method': method,
            ':path': path,
            })

        self.logger.debug('Started')
        await self.client.send_data(stream_id, payload or b'', end_stream=True)
        self.logger.debug('Sent data')
        headers = await self.client.recv_response(stream_id)
        self.logger.debug('Headers: {}'.format(headers))
        body = await self.client.read_stream(stream_id, -1)
        self.logger.debug('Body: {}'.format(body))

        resp = Response()
        resp.headers = headers
        resp.body = body
        return resp
        

