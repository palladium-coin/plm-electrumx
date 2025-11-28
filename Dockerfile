FROM lukechilds/electrumx

RUN python3 - <<'PY'
import pathlib
p = pathlib.Path('/usr/local/lib/python3.13/dist-packages/electrumx/lib/coins.py')
s = p.read_text(encoding='utf-8')

# Define Palladium coin classes directly in coins.py to avoid circular imports
palladium_classes = '''

# Palladium (PLM) - Bitcoin-based cryptocurrency
class Palladium(Bitcoin):
    NAME = "Palladium"
    SHORTNAME = "PLM"
    NET = "mainnet"

    # Address prefixes (same as Bitcoin mainnet)
    P2PKH_VERBYTE = bytes([0x00])
    P2SH_VERBYTE = bytes([0x05])
    WIF_BYTE = bytes([0x80])

    # Bech32 prefix
    HRP = "plm"

    # Genesis hash (Bitcoin mainnet)
    GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"

    # Network statistics (required by ElectrumX)
    TX_COUNT = 1000
    TX_COUNT_HEIGHT = 1
    TX_PER_BLOCK = 4

    # Default ports
    RPC_PORT = 2332
    PEER_DEFAULT_PORTS = {'t': '2333', 's': '52333'}

    # Deserializer
    DESERIALIZER = lib_tx.DeserializerSegWit


class PalladiumTestnet(Palladium):
    NAME = "Palladium"
    SHORTNAME = "tPLM"
    NET = "testnet"

    # Testnet address prefixes
    P2PKH_VERBYTE = bytes([0x7f])  # 127 decimal - addresses start with 't'
    P2SH_VERBYTE = bytes([0x73])   # 115 decimal
    WIF_BYTE = bytes([0xff])       # 255 decimal

    # Bech32 prefix for testnet
    HRP = "tplm"

    # Genesis hash (Bitcoin testnet)
    GENESIS_HASH = "000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943"

    # Network statistics (required by ElectrumX)
    TX_COUNT = 500
    TX_COUNT_HEIGHT = 1
    TX_PER_BLOCK = 2

    # Testnet ports
    RPC_PORT = 12332
    PEER_DEFAULT_PORTS = {'t': '12333', 's': '62333'}
'''

# Add Palladium classes if not already present
if 'class Palladium(Bitcoin):' not in s:
    s += palladium_classes

p.write_text(s, encoding='utf-8')

# Also patch the source file used by the container
p_src = pathlib.Path('/electrumx/src/electrumx/lib/coins.py')
if p_src.exists():
    s_src = p_src.read_text(encoding='utf-8')
    if 'class Palladium(Bitcoin):' not in s_src:
        s_src += palladium_classes
    p_src.write_text(s_src, encoding='utf-8')

print('>> Patched ElectrumX with Palladium and PalladiumTestnet coins')
PY

RUN mkdir -p /certs && \
    cat >/certs/openssl.cnf <<'EOF' && \
    openssl req -x509 -nodes -newkey rsa:4096 -days 3650 \
      -keyout /certs/server.key -out /certs/server.crt \
      -config /certs/openssl.cnf && \
    chmod 600 /certs/server.key && chmod 644 /certs/server.crt
[req]
distinguished_name = dn
x509_extensions = v3_req
prompt = no

[dn]
C  = IT
ST = -
L  = -
O  = ElectrumX
CN = plm.local

[v3_req]
keyUsage         = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName   = @alt_names

[alt_names]
DNS.1 = plm.local
IP.1  = 127.0.0.1
EOF

ENV SSL_CERTFILE=/certs/server.crt
ENV SSL_KEYFILE=/certs/server.key
