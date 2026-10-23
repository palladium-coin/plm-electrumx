# Copyright (c) 2018, John L. Jegutanis
#
# All rights reserved.
#
# See the file "LICENCE" for information about the copyright
# and warranty status of this software.

import json
import os
from binascii import unhexlify

import pytest

from electrumx.lib.coins import Coin
from electrumx.lib.hash import hash_to_hex_str

TRANSACTION_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'transactions')

# Find testcases. File names are <coin>_<net>_<id>.json,
# vout values are in satoshis.
transactions = []

for name in sorted(os.listdir(TRANSACTION_DIR)):
    name_parts = name.split("_")
    try:
        coin = Coin.lookup_coin_class(name_parts[0], name_parts[1])
        with open(os.path.join(TRANSACTION_DIR, name)) as f:
            transactions.append((coin, json.load(f)))
    except Exception:
        transactions.append(pytest.fail(name))


@pytest.fixture(params=transactions)
def transaction_details(request):
    return request.param


def test_transaction(transaction_details):
    coin, tx_info = transaction_details

    raw_tx = unhexlify(tx_info['hex'])
    tx, vsize = coin.DESERIALIZER(raw_tx, 0).read_tx_and_vsize()
    assert tx_info['txid'] == hash_to_hex_str(tx.txid_rev)
    assert tx_info['hash'] == hash_to_hex_str(tx.wtxid_rev)
    assert tx_info['version'] == tx.version
    assert tx_info['vsize'] == vsize

    vin = tx_info['vin']
    assert len(vin) == len(tx.inputs)
    for i in range(len(vin)):
        assert vin[i]['txid'] == hash_to_hex_str(tx.inputs[i].prev_txid_rev)
        assert vin[i]['vout'] == tx.inputs[i].prev_idx
        if "txinwitness" in vin[i] or (hasattr(tx, "witness") and tx.witness[i]):
            assert vin[i]["txinwitness"] == [x.hex() for x in tx.witness[i]]

    vout = tx_info['vout']
    assert len(vout) == len(tx.outputs)
    for i in range(len(vout)):
        assert vout[i]['value'] == tx.outputs[i].value
        spk = vout[i]['scriptPubKey']
        tx_pks = tx.outputs[i].pk_script
        assert spk['hex'] == tx_pks.hex()
        address, = spk["addresses"]
        assert coin.address_to_hashX(address) == coin.hashX_from_script(tx_pks)
