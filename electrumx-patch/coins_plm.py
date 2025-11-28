from electrumx.lib.coins import Bitcoin
from electrumx.lib import tx as lib_tx

class Palladium(Bitcoin):
    NAME = "Palladium"
    SHORTNAME = "PLM"
    NET = "mainnet"

    # === Prefix address ===
    P2PKH_VERBYTE = bytes([0x00])
    P2SH_VERBYTE  = bytes([0x05])
    WIF_BYTE      = bytes([0x80])

    # === bech32 prefix ===
    HRP = "plm"

    # === Genesis hash (Bitcoin mainnet) ===
    GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"

    # === Default ports ===
    RPC_PORT = 2332
    PEER_DEFAULT_PORTS = {'t': '2333', 's': '52333'}

    # === Deserializer ===
    DESERIALIZER = lib_tx.DeserializerSegWit


class PalladiumTestnet(Palladium):
    NAME = "Palladium"
    SHORTNAME = "tPLM"
    NET = "testnet"

    # === Testnet address prefixes ===
    P2PKH_VERBYTE = bytes([0x7f])  # 127 decimal - addresses start with 't'
    P2SH_VERBYTE  = bytes([0x73])  # 115 decimal
    WIF_BYTE      = bytes([0xff])  # 255 decimal

    # === Bech32 prefix for testnet ===
    HRP = "tplm"

    # === Genesis hash (Bitcoin testnet) ===
    GENESIS_HASH = "000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943"

    # === Testnet ports ===
    RPC_PORT = 12332
    PEER_DEFAULT_PORTS = {'t': '12333', 's': '62333'}

