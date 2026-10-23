# Copyright (c) 2016-2017, Neil Booth
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

'''Cryptograph hash functions and related classes.'''


import hashlib
import hmac

from electrumx.lib.util import bytes_to_int, int_to_bytes, hex_to_bytes

_sha256 = hashlib.sha256
_new_hash = hashlib.new
_hmac_digest = hmac.digest
HASHX_LEN = 11


def sha256(x: bytes) -> bytes:
    '''Simple wrapper of hashlib sha256.'''
    return _sha256(x).digest()


def double_sha256(x: bytes) -> bytes:
    '''SHA-256 of SHA-256, as used extensively in bitcoin.'''
    return sha256(sha256(x))


def hash_to_hex_str(x: bytes) -> str:
    '''Convert a big-endian binary hash to displayed hex string. (rev-to-hum)

    Display form of a binary hash is reversed and converted to hex.
    '''
    return bytes(reversed(x)).hex()


def hex_str_to_hash(x: str) -> bytes:
    '''Convert a displayed hex string to a binary hash. (hum-to-rev)'''
    return bytes(reversed(hex_to_bytes(x)))


class Base58Error(Exception):
    '''Exception used for Base58 errors.'''


class Base58:
    '''Class providing base 58 functionality.'''

    chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    assert len(chars) == 58
    cmap = {c: n for n, c in enumerate(chars)}

    @staticmethod
    def char_value(c):
        val = Base58.cmap.get(c)
        if val is None:
            raise Base58Error(f'invalid base 58 character "{c}"')
        return val

    @staticmethod
    def decode(txt):
        """Decodes txt into a big-endian bytearray."""
        if not isinstance(txt, str):
            raise TypeError('a string is required')

        if not txt:
            raise Base58Error('string cannot be empty')

        value = 0
        for c in txt:
            value = value * 58 + Base58.char_value(c)

        result = int_to_bytes(value)

        # Prepend leading zero bytes if necessary
        count = 0
        for c in txt:
            if c != '1':
                break
            count += 1
        if count:
            result = bytes(count) + result

        return result

    @staticmethod
    def encode(be_bytes):
        """Converts a big-endian bytearray into a base58 string."""
        value = bytes_to_int(be_bytes)

        txt = ''
        while value:
            value, mod = divmod(value, 58)
            txt += Base58.chars[mod]

        for byte in be_bytes:
            if byte != 0:
                break
            txt += '1'

        return txt[::-1]

    @staticmethod
    def decode_check(txt, *, hash_fn=double_sha256):
        '''Decodes a Base58Check-encoded string to a payload.  The version
        prefixes it.'''
        be_bytes = Base58.decode(txt)
        result, check = be_bytes[:-4], be_bytes[-4:]
        if check != hash_fn(result)[:4]:
            raise Base58Error(f'invalid base 58 checksum for {txt}')
        return result

    @staticmethod
    def encode_check(payload, *, hash_fn=double_sha256):
        """Encodes a payload bytearray (which includes the version byte(s))
        into a Base58Check string."""
        be_bytes = payload + hash_fn(payload)[:4]
        return Base58.encode(be_bytes)


class Bech32Error(Exception):
    '''Exception used for Bech32 and Bech32m errors.'''


class Bech32:
    '''Decoding of segwit addresses, see BIP 173 (bech32) and BIP 350 (bech32m).'''

    CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    BECH32_CONST = 1
    BECH32M_CONST = 0x2bc830a3

    @staticmethod
    def _polymod(values):
        gen = (0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)
        chk = 1
        for value in values:
            top = chk >> 25
            chk = (chk & 0x1ffffff) << 5 ^ value
            for i in range(5):
                chk ^= gen[i] if (top >> i) & 1 else 0
        return chk

    @staticmethod
    def _convert_bits(data, from_bits, to_bits):
        '''General power-of-2 base conversion without padding. Returns None if the input is invalid.'''
        acc = 0
        bits = 0
        ret = bytearray()
        maxv = (1 << to_bits) - 1
        for value in data:
            acc = (acc << from_bits) | value
            bits += from_bits
            while bits >= to_bits:
                bits -= to_bits
                ret.append((acc >> bits) & maxv)
        if bits >= from_bits or (acc << (to_bits - bits)) & maxv:
            return None
        return bytes(ret)

    @staticmethod
    def decode_segwit(hrp, address):
        '''Decode a segwit address of the given human-readable part. Returns (witness version,
        witness program) or raises Bech32Error.'''
        if not isinstance(address, str):
            raise TypeError('a string is required')
        if any(ord(c) < 33 or ord(c) > 126 for c in address):
            raise Bech32Error('invalid character in address')
        if address.lower() != address and address.upper() != address:
            raise Bech32Error('mixed case address')
        address = address.lower()
        pos = address.rfind('1')
        if pos < 1 or pos + 7 > len(address) or len(address) > 90:
            raise Bech32Error('invalid address length or separator position')
        if address[:pos] != hrp:
            raise Bech32Error(f'unexpected human-readable part "{address[:pos]}"')
        data = [Bech32.CHARSET.find(c) for c in address[pos + 1:]]
        if -1 in data:
            raise Bech32Error('invalid bech32 character')
        const = Bech32._polymod([ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp] + data)
        if const not in (Bech32.BECH32_CONST, Bech32.BECH32M_CONST):
            raise Bech32Error('invalid bech32 checksum')
        witver = data[0]
        if witver > 16:
            raise Bech32Error('invalid witness version')
        # version 0 uses bech32, later versions use bech32m
        if const != (Bech32.BECH32_CONST if witver == 0 else Bech32.BECH32M_CONST):
            raise Bech32Error('checksum does not match the witness version')
        program = Bech32._convert_bits(data[1:-6], 5, 8)
        if program is None or not 2 <= len(program) <= 40:
            raise Bech32Error('invalid witness program')
        if witver == 0 and len(program) not in (20, 32):
            raise Bech32Error('invalid witness program length for version 0')
        return witver, program
