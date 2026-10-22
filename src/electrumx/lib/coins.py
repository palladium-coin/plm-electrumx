# Copyright (c) 2016-2017, Neil Booth
# Copyright (c) 2017, the ElectrumX authors
#
# All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Module providing coin abstraction.

Anything coin-specific should go in this file and be subclassed where
necessary for appropriate handling.
'''
import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Sequence, Optional, Type

import electrumx.lib.util as util
from electrumx.lib.hash import Base58, double_sha256, hash_to_hex_str, HASHX_LEN
from electrumx.lib.script import ScriptPubKey
import electrumx.lib.tx as lib_tx
from electrumx.lib.tx import Tx
import electrumx.server.block_processor as block_proc
import electrumx.server.daemon as daemon
from electrumx.server.session import ElectrumX


@dataclass(slots=True)
class Block:
    raw: bytes
    header: bytes
    transactions: Sequence[Tx]


class CoinError(Exception):
    '''Exception raised for coin-related errors.'''


class Coin:
    '''Base class of coin hierarchy.'''

    REORG_LIMIT = 200
    # Not sure if these are coin-specific
    RPC_URL_REGEX = re.compile('.+@(\\[[0-9a-fA-F:]+\\]|[^:]+)(:[0-9]+)?')
    VALUE_PER_COIN = 100000000
    BASIC_HEADER_SIZE = 80
    STATIC_BLOCK_HEADERS = True
    SESSIONCLS = ElectrumX
    DESERIALIZER = lib_tx.Deserializer
    DAEMON = daemon.Daemon
    BLOCK_PROCESSOR = block_proc.BlockProcessor
    P2PKH_VERBYTE = bytes.fromhex("00")
    P2SH_VERBYTES = (bytes.fromhex("05"),)
    DECODE_CHECK = Base58.decode_check
    GENESIS_HASH = ('000000000019d6689c085ae165831e93'
                    '4ff763ae46a2a6c172b3f1b60a8ce26f')  # 'hum' byte-order

    # max byte-size of single jsonrpc message
    # note: we should probably be able to serve a client asking for the largest consensus-valid tx.
    #       For Bitcoin, that is 4 M weight units, i.e. 4 MB on the p2p wire.
    #       Double that due to our JSON-RPC hex-encoding, plus overhead, we need to send 8+ MB.
    #       When receiving from a client, e.g. to broadcast, such a tx would be non-standard anyway.
    DEFAULT_MAX_SEND = 8_100_000
    DEFAULT_MAX_RECV = 1_000_000

    MEMPOOL_HISTOGRAM_REFRESH_SECS = 500
    # first bin size in vbytes. smaller bins mean more precision but also bandwidth:
    MEMPOOL_COMPACT_HISTOGRAM_BINSIZE = 30_000

    # Peer discovery
    PEER_DEFAULT_PORTS = {'t': '50001', 's': '50002'}
    PEERS = []
    CRASH_CLIENT_VER = None
    BLACKLIST_URL = None
    ESTIMATEFEE_MODES = (None, 'CONSERVATIVE', 'ECONOMICAL')

    RPC_PORT: int
    NAME: str
    NET: str | None
    MIN_REQUIRED_DAEMON_VERSION: Optional[str] = None
    REQUIRED_DAEMON_INDEXES: Sequence[str] = tuple()

    # only used for initial db sync ETAs:
    TX_COUNT_HEIGHT: int  # at a given snapshot of the chain,
    TX_COUNT: int         # there have been this many txs so far,
    TX_PER_BLOCK: int     # and from that height onwards, we guess this many txs per block

    @classmethod
    def lookup_coin_class(cls, name: str, net: str) -> Type['Coin']:
        '''Return a coin class given name and network.

        Raise an exception if unrecognised.'''
        req_attrs = ('TX_COUNT', 'TX_COUNT_HEIGHT', 'TX_PER_BLOCK')
        for coin in util.subclasses(Coin):
            if (
                    coin.NAME.lower() == name.lower()
                    and coin.NET is not None
                    and coin.NET.lower() == net.lower()
            ):
                missing = [
                    attr
                    for attr in req_attrs
                    if not hasattr(coin, attr)
                ]
                if missing:
                    raise CoinError(
                        f'coin {name} missing {missing} attributes'
                    )
                return coin
        raise CoinError(f'unknown coin {name} and network {net} combination')

    @classmethod
    def sanitize_url(cls, url: str):
        # Remove surrounding ws and trailing /s
        url = url.strip().rstrip('/')
        match = cls.RPC_URL_REGEX.match(url)
        if not match:
            raise CoinError(f'invalid daemon URL: "{url}"')
        if match.groups()[1] is None:
            url = f'{url}:{cls.RPC_PORT:d}'
        if not url.startswith(('http://', 'https://')):
            url = f'http://{url}'
        return url + '/'

    @classmethod
    def max_fetch_blocks(cls, height: int) -> int:
        if height < 130000:
            return 1000
        return 100

    @classmethod
    def genesis_block(cls, block: bytes) -> bytes:
        '''Check the Genesis block is the right one for this coin.

        Return the block less its unspendable coinbase.
        '''
        header = cls.block_header(block, 0)
        header_hex_hash = hash_to_hex_str(cls.header_hash_rev(header))
        if header_hex_hash != cls.GENESIS_HASH:
            raise CoinError(f'genesis block has hash {header_hex_hash} '
                            f'expected {cls.GENESIS_HASH}')

        return header + b'\0'

    @classmethod
    def hashX_from_script(cls, script):
        '''Returns a hashX from a script.'''
        return sha256(script).digest()[:HASHX_LEN]

    @classmethod
    def address_to_hashX(cls, address):
        '''Return a hashX given a coin address.'''
        return cls.hashX_from_script(cls.pay_to_address_script(address))

    @classmethod
    def hash160_to_P2PKH_script(cls, hash160):
        return ScriptPubKey.P2PKH_script(hash160)

    @classmethod
    def hash160_to_P2PKH_hashX(cls, hash160):
        return cls.hashX_from_script(cls.hash160_to_P2PKH_script(hash160))

    @classmethod
    def pay_to_address_script(cls, address):
        '''Return a pubkey script that pays to a pubkey hash.

        Pass the address (either P2PKH or P2SH) in base58 form.
        Only used for the local RPC 'query' command (bech32 addresses are not supported).
        '''
        raw = cls.DECODE_CHECK(address)

        # Require version byte(s) plus hash160.
        verbyte = -1
        verlen = len(raw) - 20
        if verlen > 0:
            verbyte, hash160 = raw[:verlen], raw[verlen:]

        if verbyte == cls.P2PKH_VERBYTE:
            return cls.hash160_to_P2PKH_script(hash160)
        if verbyte in cls.P2SH_VERBYTES:
            return ScriptPubKey.P2SH_script(hash160)

        raise CoinError(f'invalid address: {address}')

    @classmethod
    def header_hash_rev(cls, header: bytes) -> bytes:
        '''Given a header return hash. (reverse of human-readable blockhash)'''
        return double_sha256(header)

    @classmethod
    def header_prevhash_rev(cls, header: bytes) -> bytes:
        '''Given a header return previous hash. (reverse of human-readable blockhash)'''
        return header[4:36]

    @classmethod
    def static_header_offset(cls, height: int) -> int:
        '''Given a header height return its offset in the headers file.

        If header sizes change at some point, this is the only code
        that needs updating.'''
        assert cls.STATIC_BLOCK_HEADERS
        return height * cls.BASIC_HEADER_SIZE

    @classmethod
    def static_header_len(cls, height: int) -> int:
        '''Given a header height return its length.'''
        return (cls.static_header_offset(height + 1)
                - cls.static_header_offset(height))

    @classmethod
    def block_header(cls, block: bytes, height: int) -> bytes:
        '''Returns the block header given a block and its height.'''
        return block[:cls.static_header_len(height)]

    @classmethod
    def block(cls, raw_block: bytes, height: int) -> 'Block':
        '''Return a Block namedtuple given a raw block and its height.'''
        header = cls.block_header(raw_block, height)
        txs = cls.DESERIALIZER(raw_block, start=len(header)).read_tx_block()
        return Block(raw_block, header, txs)

    @classmethod
    def decimal_value(cls, value: int) -> Decimal:
        '''Return the number of standard coin units as a Decimal given a
        quantity of smallest units.

        For example 1 BTC is returned for 100 million satoshis.
        '''
        return Decimal(value) / cls.VALUE_PER_COIN

    @classmethod
    def warn_old_client_on_tx_broadcast(cls, _client_ver):
        return False

    @classmethod
    def bucket_estimatefee_block_target(cls, n: int) -> int:
        '''For caching purposes, it might be desirable to restrict the
        set of values that can be queried as an estimatefee block target.
        '''
        return n


class Palladium(Coin):
    """Palladium (PLM), a Bitcoin Core 0.19-based chain. Standard 80-byte headers, sha256d PoW, segwit.

    Its daemon predates 'txospenderindex', 'getindexinfo' and 'submitpackage', so
    'blockchain.outpoint.subscribe' and 'blockchain.transaction.broadcast_package' will
    return daemon errors to clients. The daemon needs 'txindex=1'.
    """
    NAME = "Palladium"
    SHORTNAME = "PLM"
    NET = "mainnet"
    P2PKH_VERBYTE = bytes.fromhex("37")
    P2SH_VERBYTES = (bytes.fromhex("05"),)
    # same genesis block as Bitcoin mainnet
    GENESIS_HASH = ('000000000019d6689c085ae165831e93'
                    '4ff763ae46a2a6c172b3f1b60a8ce26f')
    MEMPOOL_HISTOGRAM_REFRESH_SECS = 120
    DESERIALIZER = lib_tx.DeserializerSegWit
    RPC_PORT = 2332
    # snapshot (UpdateTip tx= count), only used for sync ETAs
    TX_COUNT = 661_421
    TX_COUNT_HEIGHT = 542_032
    TX_PER_BLOCK = 2
    PEERS = []

    @classmethod
    def bucket_estimatefee_block_target(cls, n: int) -> int:
        # values based on https://github.com/bitcoin/bitcoin/blob/af05bd9e1e362c3148e3b434b7fac96a9a5155a1/src/policy/fees.h#L131  # noqa
        if n <= 1:
            return 1
        if n <= 12:
            return n
        if n == 25:  # so common that we make an exception for it
            return n
        if n <= 48:
            return n // 2 * 2
        if n <= 1008:
            return n // 24 * 24
        return 1008


class PalladiumTestnet(Palladium):
    SHORTNAME = "TPLM"
    NET = "testnet"
    P2PKH_VERBYTE = bytes.fromhex("7f")
    P2SH_VERBYTES = (bytes.fromhex("73"),)
    # same genesis block as Bitcoin testnet3
    GENESIS_HASH = ('000000000933ea01ad0ee984209779ba'
                    'aec3ced90fa3f408719526f8d77f4943')
    RPC_PORT = 12332
    REORG_LIMIT = 8000
    TX_COUNT = 1
    TX_COUNT_HEIGHT = 1
    TX_PER_BLOCK = 2
    PEER_DEFAULT_PORTS = {'t': '51001', 's': '51002'}


class PalladiumRegtest(PalladiumTestnet):
    NET = "regtest"
    # same genesis block as Bitcoin regtest
    GENESIS_HASH = ('0f9188f13cb7b2c71f2a335e3a4fc328'
                    'bf5beb436012afca590b1a11466e2206')
    RPC_PORT = 28443
