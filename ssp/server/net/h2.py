import os
import aioh2
import asyncio
import ssl
import collections
import re
import json
import logging

from OpenSSL import crypto, SSL
from socket import gethostname

# These are used by the auth code.
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

ROUTES = []

# Magical route-making helper.
def endpoint(routes, method=None):
    def endpoint(regex):
        def endpoint(fn):
            rx = re.compile(regex)
                    
            def route(server, proto, headers, stream_id):
                match = rx.fullmatch(headers[':path'])
                if match is None:
                    return None

                if method is not None and headers[':method'] != method:
                    return None

                return lambda: fn(server, proto, match, headers, stream_id)

            routes.append(route)
        return endpoint
    return endpoint

for k,v in {
        'get': 'GET',
        'post': 'POST',
        }.items():
    locals()[k] = endpoint(ROUTES, v)
endpoint = endpoint(ROUTES)

def _verify_machine_auth(server, headers):
    machine = headers.get('machine')
    if machine is None:
        return None
        
    machine = server.universe.machines.get(machine)
    if machine is None:
        return None

    mach_id = verify_machine_auth(headers, machine.id, machine.secret)
    if mach_id is None:
        return None

    return machine
        
def server_verify_machine_auth(server, proto, stream_id, headers, fatal=True):
    machine = _verify_machine_auth(server, headers)
    if fatal and (machine is None):
        proto.send_headers(stream_id, (
            (':status', '401'),
            ('content-type', 'application/json'),
        ))
        proto.send_data(stream_id, b'{}', end_stream=True)
        return

    return machine

@post('/machines/?')
async def new_machine(server, proto, match, headers, stream_id):
    mach = server.universe.create_machine()

    await proto.send_headers(stream_id, (
        (':status', '200'),
        ('content-type', 'application/json'),
    ))
    payload = json.dumps({
        'success': True,
        'id': mach.id,
        'secret': mach.secret,
    }).encode('utf-8')
    await proto.send_data(stream_id, payload, end_stream=True)

@post('/machines/([^/]*)/start-process')
async def machine_start_process(server, proto, match, headers, stream_id):
    mach = server_verify_machine_auth(server, proto, stream_id, headers)
    if mach is None:
        return

    proc = mach.start_process(b'')
    
    response_headers = (
        (':status', '200'),
        ('content-type', 'application/json'),
        ('pid', proc.pid)
    )
    await proto.send_headers(stream_id, response_headers, end_stream=True)

class H2Server(object):
    def __init__(self, server):
        self.server = server
        self.exiting = False

        self.pending_tasks = []
        self.pending_clients = []

    def wait_for(self, future, client=False):
        self.pending_tasks.append(future)
        if client:
            self.pending_clients.append(future)

        def cleanup():
            self.pending_tasks.remove(future)
            if client:
                self.pending_clients.remove(future)
            
        future.add_done_callback(lambda _: cleanup)

    async def handle_request(self, proto, stream_id, headers):
        headers = collections.OrderedDict(headers)
        
        done = False
        for route in ROUTES:
            fn = route(self.server, proto, headers, stream_id)
            if (fn is not None):
                await fn()
                done = True
                break
            
        if done is True:
            return

        logger.debug('404: {} {}'.format(headers.get(':method', ''), headers.get(':path', '')))
        response_headers = (
            (':status', '404'),
        )
        proto.send_headers(stream_id, response_headers, end_stream=True)

    async def handle_client(self, proto):
        while not self.exiting:
            stream_id, headers = await proto.recv_request()
            logger.debug('request: {}'.format(headers))
            self.wait_for(self.server.loop.create_task(self.handle_request(proto, stream_id, headers)))

    def start_client(self, proto):
        self.wait_for(self.server.loop.create_task(self.handle_client(proto)), client=True)

    @property
    def sockets(self):
        return self.proto.sockets

    async def close(self):
        self.exiting = True
        self.proto.close()

        for client in self.pending_clients:
            client.cancel()

        if len(self.pending_tasks) > 0:
            await asyncio.wait(self.pending_tasks)

async def start_server(server, host=None, port=0, **kw):
    h2_server = H2Server(server)
    h2_server.proto = await aioh2.start_server(
        lambda p: h2_server.start_client(p),
        loop=server.loop,
        ssl=create_ssl_context(),
        host=host,
        port=port,
        **kw)

    return h2_server

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
