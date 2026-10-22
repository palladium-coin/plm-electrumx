# Tests of the Palladium coin classes (parameters from palladiumcore src/chainparams.cpp)

import pytest

from electrumx.lib import tx as lib_tx
from electrumx.lib.coins import Coin, Palladium, PalladiumTestnet, PalladiumRegtest

# (class, net, rpc port, P2PKH verbyte, P2SH verbyte, genesis hash)
PARAMS = [
    (Palladium, "mainnet", 2332, "37", "05",
     "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"),
    (PalladiumTestnet, "testnet", 12332, "7f", "73",
     "000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943"),
    (PalladiumRegtest, "regtest", 28443, "7f", "73",
     "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206"),
]


@pytest.mark.parametrize("coin,net,rpc_port,p2pkh,p2sh,genesis", PARAMS)
def test_chain_params(coin, net, rpc_port, p2pkh, p2sh, genesis):
    assert coin.NAME == "Palladium"
    assert coin.NET == net
    assert coin.RPC_PORT == rpc_port
    assert coin.P2PKH_VERBYTE == bytes.fromhex(p2pkh)
    assert coin.P2SH_VERBYTES == (bytes.fromhex(p2sh),)
    assert coin.GENESIS_HASH == genesis
    assert coin.BASIC_HEADER_SIZE == 80
    assert coin.DESERIALIZER is lib_tx.DeserializerSegWit


@pytest.mark.parametrize("coin,net", [(c, n) for c, n, *_ in PARAMS])
def test_lookup_coin_class(coin, net):
    assert Coin.lookup_coin_class("Palladium", net) is coin
    assert Coin.lookup_coin_class("palladium", net.upper()) is coin


def test_daemon_requirements_disabled():
    # Palladium Core (Bitcoin Core 0.19 based) has no getindexinfo/txospenderindex
    for coin, *_ in PARAMS:
        assert coin.MIN_REQUIRED_DAEMON_VERSION is None
        assert not coin.REQUIRED_DAEMON_INDEXES
