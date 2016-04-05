import os
import asyncio
import ssl
import collections
import re

from h2.connection import H2Connection
from h2.events import DataReceived, RequestReceived

from OpenSSL import crypto, SSL
from socket import gethostname

class Route(object):
    pass

class H2Protocol(asyncio.Protocol):
    ROUTES = []
    
    def __init__(self, server):
        self.server = server
        self.conn = H2Connection(client_side=False)
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def data_received(self, data):
        events = self.conn.receive_data(data)
        self.transport.write(self.conn.data_to_send())

        for event in events:
            if isinstance(event, RequestReceived):
                self.request_received(event.headers, event.stream_id)
            elif isinstance(event, DataReceived):
                self.conn.reset_stream(event.stream_id)

            self.transport.write(self.conn.data_to_send())

    def request_received(self, headers, stream_id):
        headers = collections.OrderedDict(headers)
        
        done = False
        for route in self.ROUTES:
            if route(self, headers, stream_id):
                done = True
                break
            
        if done is True:
            return

        response_headers = (
            (':status', '404'),
            ('content-type', 'application/json'),
        )
        self.conn.send_headers(stream_id, response_headers, end_stream=True)

    # Magical route-making helper.
    def endpoint(routes, method=None):
        def endpoint(regex):
            def endpoint(fn):
                rx = re.compile(regex)
                    
                def route(self, headers, stream_id):
                    match = rx.fullmatch(headers[':path'])
                    if match is None:
                        return False

                    if method is not None and headers[':method'] != method:
                        return False

                    fn(self, match, headers, stream_id)
                    return True

                routes.append(route)
            return endpoint
        return endpoint
    for k,v in {
            'get': 'GET',
            'post': 'POST',
            }.items():
        locals()[k] = endpoint(ROUTES, v)
    endpoint = endpoint(ROUTES)

    @get('/node/([^/]*)')
    def node(self, match, headers, stream_id):
        response_headers = (
            (':status', '200'),
            ('content-type', 'application/json'),
            ('node-id', match.group(1)),
        )
        self.conn.send_headers(stream_id, response_headers, end_stream=True)

    @post('/node/([^/]*)')
    def node(self, match, headers, stream_id):
        response_headers = (
            (':status', '200'),
            ('content-type', 'application/json'),
            ('node-id', match.group(1)),
        )
        self.conn.send_headers(stream_id, response_headers, end_stream=True)
    

def h2_protocol(server):
    return lambda: H2Protocol(server)

def get_config_path():
    home = os.environ.get('HOME')
    if home is None:
        home = os.environ.get('APPDATA')

    if home is None:
        raise Exception('No $HOME path set.')
    
    path = os.path.join(home, '.ssp')
    if not os.path.isdir(path):
        os.mkdir(path)
    return path

def _get_debug_ssl_certificate():
    conf_path = get_config_path()

    crt_path = os.path.join(conf_path, 'cert.crt')
    key_path = os.path.join(conf_path, 'cert.key')
    
    if not os.path.isfile(crt_path) or not os.path.isfile(key_path):
        # Generate certificate
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 1024)
 
        # CREATE A SELF-SIGNED CERT
        cert = crypto.X509()
        cert.get_subject().C = "UK"
        cert.get_subject().ST = "London"
        cert.get_subject().L = "London"
        cert.get_subject().O = "Supersonic Shiny Proton"
        cert.get_subject().OU = "Supersonic Shiny Proton"
        cert.get_subject().CN = gethostname()
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha1')
 
        with open(crt_path, 'wb') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_path, 'wb') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    return [crt_path, key_path]
    

def create_ssl_context():
    cert = _get_debug_ssl_certificate()
    
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.options |= (
        ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
    )
    ssl_context.set_ciphers("ECDHE+AESGCM")
    ssl_context.load_cert_chain(certfile=cert[0], keyfile=cert[1])
    ssl_context.set_alpn_protocols(["h2"])
    return ssl_context
