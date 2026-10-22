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
# and warranty status of this software.

'''Transaction-related classes and functions.'''

from dataclasses import dataclass
from typing import Sequence, Optional, Tuple

from electrumx.lib.hash import double_sha256, hash_to_hex_str
from electrumx.lib.util import (
    unpack_le_int32_from, unpack_le_int64_from, unpack_le_uint16_from,
    unpack_be_uint16_from,
    unpack_le_uint32_from, unpack_le_uint64_from, pack_le_int32, pack_varint,
    pack_le_uint32, pack_le_int64, pack_varbytes,
)

ZERO = bytes(32)
MINUS_1 = 4294967295


class SkipTxDeserialize(Exception):
    '''Exception used to indicate transactions that should be skipped
    on account of certain deserialization issues.
    '''


# note: slotted dataclasses are a bit faster than namedtuples
# note: frozen dataclasses are much slower than non-frozen
#       ref https://rednafi.com/python/statically-enforcing-frozen-dataclasses/
@dataclass(kw_only=True, slots=True)
class Tx:
    '''Class representing a transaction.'''
    version: int
    inputs: Sequence['TxInput']
    outputs: Sequence['TxOutput']
    locktime: int
    # For efficiency, we store/process tx hashes in the natural serialized order ("rev").
    # This is the reverse of the usual human display byteorder ("hum").
    txid_rev: bytes
    wtxid_rev: bytes

    def serialize(self):
        return b''.join((
            pack_le_int32(self.version),
            pack_varint(len(self.inputs)),
            b''.join(tx_in.serialize() for tx_in in self.inputs),
            pack_varint(len(self.outputs)),
            b''.join(tx_out.serialize() for tx_out in self.outputs),
            pack_le_uint32(self.locktime)
        ))


@dataclass(kw_only=True, slots=True)
class TxInput:
    '''Class representing a transaction input.'''
    prev_txid_rev: bytes
    prev_idx: int
    script: bytes
    sequence: int

    def __str__(self):
        script = self.script.hex()
        prev_hash = hash_to_hex_str(self.prev_txid_rev)
        return (f"Input({prev_hash}, {self.prev_idx:d}, script={script}, "
                f"sequence={self.sequence:d})")

    def is_generation(self):
        '''Test if an input is generation/coinbase like'''
        return self.prev_idx == MINUS_1 and self.prev_txid_rev == ZERO

    def serialize(self):
        return b''.join((
            self.prev_txid_rev,
            pack_le_uint32(self.prev_idx),
            pack_varbytes(self.script),
            pack_le_uint32(self.sequence),
        ))


@dataclass(kw_only=True, slots=True)
class TxOutput:
    value: int
    pk_script: bytes

    def serialize(self):
        return b''.join((
            pack_le_int64(self.value),
            pack_varbytes(self.pk_script),
        ))


@dataclass(kw_only=True, slots=True, frozen=True)
class TXOSpendStatus:
    funder_height: Optional[int]  # block height TXO is mined at. None if the outpoint never existed
    spender_txid_rev: Optional[bytes] = None
    spender_height: Optional[int] = None

    def __post_init__(self):
        assert (self.spender_txid_rev is not None) == (self.spender_height is not None), (self.spender_txid_rev, self.spender_height)


TxOutpoint = tuple[bytes, int]  # (txid_rev, txout_idx)


class Deserializer:
    '''Deserializes blocks into transactions.

    External entry points are read_tx(),
    read_tx_and_vsize() and read_block().

    This code is performance sensitive as it is executed 100s of
    millions of times during sync.
    '''

    TX_HASH_FN = staticmethod(double_sha256)  # returns txid_rev

    def __init__(self, binary, start=0):
        assert isinstance(binary, bytes)
        self.binary = binary  # note: this might be a full block or just a raw tx
        self._binary_length = len(binary)
        self.cursor = start

    def read_tx(self) -> Tx:
        '''Return a deserialized transaction.'''
        start = self.cursor
        tx = Tx(
            version=self._read_le_int32(),
            inputs=self._read_inputs(),
            outputs=self._read_outputs(),
            locktime=self._read_le_uint32(),
            txid_rev=None,
            wtxid_rev=None,
        )
        txid = self.TX_HASH_FN(self.binary[start:self.cursor])
        tx.txid_rev = txid
        tx.wtxid_rev = txid
        return tx

    def read_tx_and_vsize(self) -> Tuple[Tx, int]:
        '''Return a (deserialized TX, vsize) tuple.'''
        return self._read_tx_parts()

    def _read_tx_parts(self) -> Tuple[Tx, int]:
        '''Return a (deserialized TX, vsize) tuple.'''
        start = self.cursor
        tx = self.read_tx()
        return tx, self.cursor - start

    def read_tx_block(self) -> Sequence[Tx]:
        read = self.read_tx
        # Some coins have excess data beyond the end of the transactions
        return [read() for _ in range(self._read_varint())]

    def _read_inputs(self):
        read_input = self._read_input
        return [read_input() for i in range(self._read_varint())]

    def _read_input(self):
        return TxInput(
            prev_txid_rev=self._read_nbytes(32),
            prev_idx=self._read_le_uint32(),
            script=self._read_varbytes(),
            sequence=self._read_le_uint32(),
        )

    def _read_outputs(self):
        read_output = self._read_output
        return [read_output() for i in range(self._read_varint())]

    def _read_output(self):
        return TxOutput(
            value=self._read_le_int64(),
            pk_script=self._read_varbytes(),
        )

    def _read_byte(self):
        cursor = self.cursor
        self.cursor += 1
        return self.binary[cursor]

    def _read_nbytes(self, n):
        cursor = self.cursor
        self.cursor = end = cursor + n
        assert self._binary_length >= end
        return self.binary[cursor:end]

    def _read_varbytes(self):
        return self._read_nbytes(self._read_varint())

    def _read_varint(self):
        n = self.binary[self.cursor]
        self.cursor += 1
        if n < 253:
            return n
        if n == 253:
            return self._read_le_uint16()
        if n == 254:
            return self._read_le_uint32()
        return self._read_le_uint64()

    def _read_le_int32(self):
        result, = unpack_le_int32_from(self.binary, self.cursor)
        self.cursor += 4
        return result

    def _read_le_int64(self):
        result, = unpack_le_int64_from(self.binary, self.cursor)
        self.cursor += 8
        return result

    def _read_le_uint16(self):
        result, = unpack_le_uint16_from(self.binary, self.cursor)
        self.cursor += 2
        return result

    def _read_be_uint16(self):
        result, = unpack_be_uint16_from(self.binary, self.cursor)
        self.cursor += 2
        return result

    def _read_le_uint32(self):
        result, = unpack_le_uint32_from(self.binary, self.cursor)
        self.cursor += 4
        return result

    def _read_le_uint64(self):
        result, = unpack_le_uint64_from(self.binary, self.cursor)
        self.cursor += 8
        return result


@dataclass(kw_only=True, slots=True)
class TxSegWit(Tx):
    '''Class representing a SegWit transaction.'''
    marker: int
    flag: int
    witness: Sequence


class DeserializerSegWit(Deserializer):

    # https://bitcoincore.org/en/segwit_wallet_dev/#transaction-serialization

    def _read_witness(self, fields):
        read_witness_field = self._read_witness_field
        return [read_witness_field() for i in range(fields)]

    def _read_witness_field(self):
        read_varbytes = self._read_varbytes
        return [read_varbytes() for i in range(self._read_varint())]

    def _read_tx_parts(self) -> Tuple[Tx, int]:
        '''Return a (deserialized TX, vsize) tuple.'''
        orig_start = self.cursor
        start = self.cursor
        marker = self.binary[self.cursor + 4]
        if marker:  # non-segwit
            tx = Deserializer.read_tx(self)
            return tx, self.cursor - orig_start

        # Ugh, this is tasty.
        version = self._read_le_int32()
        orig_ser = self.binary[start:self.cursor]

        marker = self._read_byte()
        flag = self._read_byte()

        start = self.cursor
        inputs = self._read_inputs()
        outputs = self._read_outputs()
        orig_ser += self.binary[start:self.cursor]

        witness_start = self.cursor
        witness = self._read_witness(len(inputs))
        witness_size = self.cursor - witness_start + 2  # +2 due to marker and flag bytes

        start = self.cursor
        locktime = self._read_le_uint32()
        orig_ser += self.binary[start:self.cursor]
        base_size = self.cursor - orig_start - witness_size
        weight = 4 * base_size + witness_size
        vsize = weight // 4 + (weight % 4 > 0)

        txid = self.TX_HASH_FN(orig_ser)
        wtxid = self.TX_HASH_FN(self.binary[orig_start:self.cursor])

        return TxSegWit(
            version=version,
            marker=marker,
            flag=flag,
            inputs=inputs,
            outputs=outputs,
            witness=witness,
            locktime=locktime,
            txid_rev=txid,
            wtxid_rev=wtxid), vsize

    def read_tx(self):
        return self._read_tx_parts()[0]
