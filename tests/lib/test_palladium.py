# Tests of the Palladium coin classes (parameters of the Palladium Core chain params)

import pytest

from electrumx.lib import tx as lib_tx
from electrumx.lib.coins import Coin, Palladium, PalladiumTestnet, PalladiumRegtest
from electrumx.lib.hash import Base58Error, Bech32, Bech32Error
from electrumx.lib.script import ScriptPubKey

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


@pytest.mark.parametrize("coin,shortname", [(Palladium, "PLM"), (PalladiumTestnet, "TPLM"), (PalladiumRegtest, "RPLM")])
def test_shortname(coin, shortname):
    assert coin.SHORTNAME == shortname


@pytest.mark.parametrize("coin,net", [(c, n) for c, n, *_ in PARAMS])
def test_lookup_coin_class(coin, net):
    assert Coin.lookup_coin_class("Palladium", net) is coin
    assert Coin.lookup_coin_class("palladium", net.upper()) is coin


def test_daemon_requirements_disabled():
    # Palladium Core has no getindexinfo/txospenderindex
    for coin, *_ in PARAMS:
        assert coin.MIN_REQUIRED_DAEMON_VERSION is None
        assert not coin.REQUIRED_DAEMON_INDEXES


def bech32_encode_v0(hrp, program):
    """Minimal bech32 encoder of a witness v0 address, only to build test addresses"""
    charset = Bech32.CHARSET
    acc = bits = 0
    data = [0]
    for byte in program:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            data.append((acc >> bits) & 31)
    if bits:
        data.append((acc << (5 - bits)) & 31)
    values = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp] + data
    polymod = Bech32._polymod(values + [0] * 6) ^ Bech32.BECH32_CONST
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(charset[d] for d in data + checksum)


# bech32 / bech32m: the valid and invalid segwit addresses of BIP 173 and BIP 350
BIP_VALID = [
    ("bc", "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4", 0, "751e76e8199196d454941c45d1b3a323f1433bd6"),
    ("tb", "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7", 0,
     "1863143c14c5166804bd19203356da136c985678cd4d27a1b8c6329604903262"),
    ("bc", "bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kt5nd6y", 1,
     "751e76e8199196d454941c45d1b3a323f1433bd6751e76e8199196d454941c45d1b3a323f1433bd6"),
    ("bc", "BC1SW50QGDZ25J", 16, "751e"),
]
BIP_INVALID = [
    ("bc", "tc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vq5zuyut"),   # wrong hrp
    ("bc", "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd"),   # bech32 for version 1
    ("bc", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kemeawh"),                       # bech32m for version 0
    ("bc", "BC1S0XLXVLHEMJA6C4DQV22UAPCTQUPFHLXM9H8Z3K2E72Q4K9HCZ7VQ54WELL"),   # bad checksum
    ("bc", "Bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"),                       # mixed case
    ("bc", "bc1gmk9yu"),                                                        # empty program
    ("bc", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5"),                       # bad checksum
]


@pytest.mark.parametrize("hrp,address,witver,program", BIP_VALID)
def test_bech32_decode_segwit(hrp, address, witver, program):
    assert Bech32.decode_segwit(hrp, address) == (witver, bytes.fromhex(program))


@pytest.mark.parametrize("hrp,address", BIP_INVALID)
def test_bech32_decode_segwit_invalid(hrp, address):
    with pytest.raises(Bech32Error):
        Bech32.decode_segwit(hrp, address)


def test_segwit_script():
    assert ScriptPubKey.segwit_script(0, bytes(20)) == b"\x00\x14" + bytes(20)
    assert ScriptPubKey.segwit_script(1, bytes(32)) == b"\x51\x20" + bytes(32)
    assert ScriptPubKey.segwit_script(16, b"\x75\x1e") == b"\x60\x02\x75\x1e"


@pytest.mark.parametrize("coin,hrp", [(Palladium, "plm"), (PalladiumTestnet, "tplm"), (PalladiumRegtest, "rplm")])
def test_bech32_address_to_script(coin, hrp):
    assert coin.BECH32_HRP == hrp
    # a v0 witness keyhash address built from a known hash160 (the checksum is computed with a constant)
    h160 = bytes.fromhex("751e76e8199196d454941c45d1b3a323f1433bd6")
    address = bech32_encode_v0(hrp, h160)
    assert coin.pay_to_address_script(address) == b"\x00\x14" + h160
    assert coin.pay_to_address_script(address.upper()) == b"\x00\x14" + h160
    assert coin.address_to_hashX(address) == coin.hashX_from_script(b"\x00\x14" + h160)


def test_bech32_address_of_another_network_is_rejected():
    address = bech32_encode_v0("tplm", bytes(20))
    with pytest.raises((Base58Error, Bech32Error)):  # not a mainnet bech32 address, so it is read as base58
        Palladium.pay_to_address_script(address)
