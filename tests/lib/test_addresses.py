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

import pytest

import electrumx.lib.coins as coins

addresses = [
    # addresses and scripts from palladiumcore src/test/data/key_io_valid.json
    (coins.Palladium, "PHrYiyUQTSekTWvVBNMEnSzV1DCB9TGR2P",
     "65a16059864a2fdbc7c99a4723a8395bc6f188eb", "0fae27c959f6b69f711a9e"),
    (coins.Palladium, "3CMNFxN1oHBc4R1EpboAL5yzHGgE611Xou",
     "74f209f6ea907e2ea48f74fae05782ae8a665257", "0ec76b02c1f59dcc3d8b6c"),
    (coins.PalladiumTestnet, "tEZSNGVUiXapct4zsnZcfz9CfqKhmUqguv",
     "53c0307d6851aa0ce7825ba883c6bd9ad242b486", "bec4c9c9872501d067633d"),
    (coins.PalladiumTestnet, "oRvMM9SjaZ8LpnNkN7R8MLj5ZtADdTxKan",
     "6349a418fc4578d10a372b54b45c280cc8c4382f", "272f0d99c753fb3af434aa"),
]


@pytest.fixture(params=addresses)
def address(request):
    return request.param


def test_address_to_hashX(address):
    coin, addr, _, hashX = address
    assert coin.address_to_hashX(addr).hex() == hashX
