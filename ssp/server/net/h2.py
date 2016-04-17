import os
import asyncio
import ssl
import collections
import re
import json
import logging

import hmac
import hashlib
import random
import string

logger = logging.getLogger(__name__)

def _get_signature(headers, id, key):
    nonce = headers.get('nonce', '')
    method = headers.get(':method', '')
    path = headers.get(':path', '')

    hm = hmac.new(key.encode('utf-8'), digestmod=hashlib.sha256)
    hm.update(id.encode('utf-8'))
    hm.update(nonce.encode('utf-8'))
    hm.update(method.encode('utf-8'))
    hm.update(path.encode('utf-8'))

    return hm.hexdigest()

def sign_machine_auth(headers, id, key):
    rand = random.SystemRandom()
    charset = string.ascii_uppercase
    nonce = ''.join(rand.choice(charset) for _ in range(20))
    
    headers['machine'] = id
    headers['nonce'] = nonce
    headers['signature'] = _get_signature(headers, id, key)

def verify_machine_auth(headers, id, key):
    machine = headers.get('machine')
    if machine is None:
        return None

    signature = _get_signature(headers, id, key)
    existing = headers.get('signature', '')
    if signature == existing:
        return machine

    logger.warning('signing error for {}'.format(machine))
    return None

from h2.connection import H2Connection
from h2.events import RequestReceived

from OpenSSL import crypto, SSL
from socket import gethostname

class Route(object):
    pass

class H2Protocol(asyncio.Protocol):
    ROUTES = []
    
    def __init__(self, loop, server):
        self.loop = loop
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

            self.transport.write(self.conn.data_to_send())

    def request_received(self, headers, stream_id):
        self.loop.create_task(self.request_coro(headers, stream_id))

    async def request_coro(self, headers, stream_id):
        headers = collections.OrderedDict(headers)

        done = False
        for route in self.ROUTES:
            fn = route(self, headers, stream_id)
            if (fn is not None):
                await fn()
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
                        return None

                    if method is not None and headers[':method'] != method:
                        return None

                    return lambda: fn(self, match, headers, stream_id)

                routes.append(route)
            return endpoint
        return endpoint
    for k,v in {
            'get': 'GET',
            'post': 'POST',
            }.items():
        locals()[k] = endpoint(ROUTES, v)
    endpoint = endpoint(ROUTES)

    def _verify_machine_auth(self, headers):
        machine = headers.get('machine')
        if machine is None:
            return None
        
        machine = self.server.universe.machines.get(machine)
        if machine is None:
            return None

        mach_id = verify_machine_auth(headers, machine.id, machine.secret)
        if mach_id is None:
            return None

        return machine
        
    def verify_machine_auth(self, stream_id, headers, fatal=True):
        machine = self._verify_machine_auth(headers)
        if fatal and (machine is None):
            self.conn.send_headers(stream_id, (
                (':status', '401'),
                ('content-type', 'application/json'),
            ))
            self.conn.send_data(stream_id, b'{}', end_stream=True)
            return

        return machine
        
    @get('/machines/([^/]*)')
    async def machine(self, match, headers, stream_id):
        response_headers = (
            (':status', '200'),
            ('content-type', 'application/json'),
            ('node-id', match.group(1)),
        )
        self.conn.send_headers(stream_id, response_headers, end_stream=True)

    @post('/machines/?')
    async def new_machine(self, match, headers, stream_id):
        mach = self.server.universe.create_machine()
        
        self.conn.send_headers(stream_id, (
            (':status', '200'),
            ('content-type', 'application/json'),
        ))
        payload = json.dumps({
            'success': True,
            'id': mach.id,
            'secret': mach.secret,
        }).encode('utf-8')
        self.conn.send_data(stream_id, payload, end_stream=True)

    @post('/machines/([^/]*)/start-process')
    async def machine_start_process(self, match, headers, stream_id):
        mach = self.verify_machine_auth(stream_id, headers)
        if mach is None:
            return

        proc = mach.start_process(b'')
        
        response_headers = (
            (':status', '200'),
            ('content-type', 'application/json'),
            ('pid', proc.pid)
        )
        self.conn.send_headers(stream_id, response_headers, end_stream=True)
    

def h2_protocol(*a, **kw):
    return lambda: H2Protocol(*a, **kw)

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
