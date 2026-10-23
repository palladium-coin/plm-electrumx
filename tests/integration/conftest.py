'''Integration tests: ElectrumX against a real Palladium node in regtest mode.

They are skipped unless PLM_TEST_DAEMON_URL is set, so a plain `pytest` does not need a node. To run them:

    docker compose -f tests/integration/docker-compose.yml up -d --build --wait
    PLM_TEST_DAEMON_URL=http://plmtest:plmtest@127.0.0.1:28443/ pytest tests/integration

PLM_TEST_DB_ENGINE (default leveldb) selects the database engine of the server under test.
'''
import base64
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from hashlib import sha256
from pathlib import Path

import pytest

DAEMON_URL = os.environ.get('PLM_TEST_DAEMON_URL')
REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_HEIGHT = 130


def pytest_collection_modifyitems(config, items):
    if DAEMON_URL:
        return
    skip = pytest.mark.skip(reason='PLM_TEST_DAEMON_URL not set (no regtest node)')
    here = Path(__file__).parent
    for item in items:
        if here in Path(str(item.fspath)).parents:
            item.add_marker(skip)


class Node:
    '''Minimal JSON-RPC client of the regtest node.'''

    def __init__(self, url):
        parts = urllib.parse.urlsplit(url)
        auth = base64.b64encode(f'{parts.username}:{parts.password}'.encode()).decode()
        self.url = f'{parts.scheme}://{parts.hostname}:{parts.port}/'
        self.headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}

    def call(self, method, *params, wallet=None):
        url = self.url + (f'wallet/{wallet}' if wallet is not None else '')
        body = json.dumps({'jsonrpc': '1.0', 'id': 'test', 'method': method, 'params': list(params)}).encode()
        req = urllib.request.Request(url, body, self.headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                reply = json.load(resp)
        except urllib.error.HTTPError as e:  # the node answers errors with HTTP 500 and a JSON body
            reply = json.load(e)
        if reply.get('error'):
            raise RuntimeError(f'{method}: {reply["error"]}')
        return reply['result']

    def mine(self, n, address):
        return self.call('generatetoaddress', n, address)


@pytest.fixture(scope='session')
def node():
    node = Node(DAEMON_URL)
    deadline = time.monotonic() + 60
    while True:
        try:
            node.call('getblockcount')
            break
        except Exception:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)
    return node


@pytest.fixture(scope='session')
def wallet(node):
    '''Name of a loaded wallet (the node may or may not create a default one)'''
    if not node.call('listwallets'):
        node.call('createwallet', 'test')
    return node.call('listwallets')[0]


def new_address(node, wallet):
    return node.call('getnewaddress', wallet=wallet)


def scripthash(node, address):
    '''Electrum scripthash of an address of the node's wallet: sha256 of the scriptPubKey, byte-reversed'''
    script = bytes.fromhex(node.call('getaddressinfo', address)['scriptPubKey'])
    return sha256(script).digest()[::-1].hex()


class ElectrumClient:
    '''Newline-delimited JSON-RPC over TCP, one request at a time (notifications are skipped).'''

    def __init__(self, port, ssl_context=None):
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=30)
        if ssl_context:
            self.sock = ssl_context.wrap_socket(self.sock, server_hostname='localhost')
        self.file = self.sock.makefile('rwb')
        self.next_id = 0

    def call(self, method, *params):
        self.next_id += 1
        msg = {'jsonrpc': '2.0', 'id': self.next_id, 'method': method, 'params': list(params)}
        self.file.write(json.dumps(msg).encode() + b'\n')
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if reply.get('id') == self.next_id:
                if 'error' in reply:
                    raise RuntimeError(f'{method}: {reply["error"]}')
                return reply['result']

    def close(self):
        self.file.close()
        self.sock.close()


# set by the electrumx fixture: the SSL port of the server under test and the certificate it presents
SSL_SERVICE = {}


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@pytest.fixture(scope='session')
def electrumx(node, wallet):
    '''Starts electrumx_server on an empty database, against the regtest node. Yields the TCP port.'''
    # long enough to have mature coinbases to spend (COINBASE_MATURITY is 120 on Palladium)
    miner = new_address(node, wallet)
    if node.call('getblockcount') < MIN_HEIGHT:
        node.mine(MIN_HEIGHT - node.call('getblockcount'), miner)
    port = free_port()
    ssl_port = free_port()
    with tempfile.TemporaryDirectory() as db_dir:
        certfile = os.path.join(db_dir, 'server.crt')
        keyfile = os.path.join(db_dir, 'server.key')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1', '-keyout', keyfile, '-out', certfile],
                       check=True, capture_output=True)
        SSL_SERVICE.update(port=ssl_port, certfile=certfile)
        env = dict(os.environ,
                   COIN='Palladium', NET='regtest',
                   DB_ENGINE=os.environ.get('PLM_TEST_DB_ENGINE', 'leveldb'), DB_DIRECTORY=db_dir,
                   DAEMON_URL=DAEMON_URL, SERVICES=f'tcp://127.0.0.1:{port},ssl://127.0.0.1:{ssl_port}',
                   SSL_CERTFILE=certfile, SSL_KEYFILE=keyfile,
                   PEER_DISCOVERY='off', PEER_ANNOUNCE='', LOG_LEVEL='info')
        log = open(os.path.join(db_dir, 'electrumx.log'), 'w+')
        proc = subprocess.Popen([sys.executable, str(REPO_ROOT / 'electrumx_server')], cwd=REPO_ROOT, env=env,
                                stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while True:
                if proc.poll() is not None:
                    log.seek(0)
                    pytest.fail(f'electrumx_server exited with {proc.returncode}:\n{log.read()}')
                try:
                    socket.create_connection(('127.0.0.1', port), timeout=1).close()
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        log.seek(0)
                        pytest.fail(f'electrumx_server did not start:\n{log.read()}')
                    time.sleep(0.5)
            yield port
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.close()


def wait_for(predicate, what, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() > deadline:
            raise AssertionError(f'timeout waiting for {what}')
        time.sleep(0.5)
