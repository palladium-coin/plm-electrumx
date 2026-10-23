'''ElectrumX server end to end against a Palladium regtest node (see conftest.py).'''
import pytest

from electrumx.lib.coins import PalladiumRegtest
from tests.integration.conftest import ElectrumClient, new_address, scripthash, wait_for


def test_node_matches_coin_parameters(node):
    info = node.call('getblockchaininfo')
    assert info['chain'] == 'regtest'
    genesis = node.call('getblockhash', 0)
    assert genesis == PalladiumRegtest.GENESIS_HASH
    # the coin class accepts the genesis block that the node serves
    raw = bytes.fromhex(node.call('getblock', genesis, 0))
    assert PalladiumRegtest.genesis_block(raw) == raw[:80] + b'\0'


def test_address_prefixes_match_the_node(node, wallet):
    '''A legacy (base58) address of the node's wallet maps to the hashX of its script'''
    address = node.call('getnewaddress', '', 'legacy', wallet=wallet)
    script = bytes.fromhex(node.call('getaddressinfo', address)['scriptPubKey'])
    assert PalladiumRegtest.address_to_hashX(address) == PalladiumRegtest.hashX_from_script(script)


@pytest.fixture
def client(electrumx):
    client = ElectrumClient(electrumx)
    yield client
    client.close()


def test_server_syncs_and_follows_the_chain(node, wallet, electrumx, client):
    client.call('server.version', 'plm-integration-test', '1.4')
    wait_for(lambda: client.call('blockchain.headers.subscribe')['height'] == node.call('getblockcount'),
             'the server to reach the node height')
    tip = client.call('blockchain.headers.subscribe')
    assert tip['height'] == node.call('getblockcount')

    node.mine(3, new_address(node, wallet))
    wait_for(lambda: client.call('blockchain.headers.subscribe')['height'] == tip['height'] + 3,
             'the server to follow new blocks')
    header = client.call('blockchain.block.header', tip['height'] + 3)
    assert PalladiumRegtest.header_hash_rev(bytes.fromhex(header)) == bytes.fromhex(node.call('getbestblockhash'))[::-1]


def test_balance_history_and_mempool(node, wallet, electrumx, client):
    client.call('server.version', 'plm-integration-test', '1.4')
    miner = new_address(node, wallet)
    node.mine(1, miner)
    target = node.call('getnewaddress', '', 'bech32', wallet=wallet)
    sh = scripthash(node, target)

    # unconfirmed: seen in the server's mempool
    txid = node.call('sendtoaddress', target, 1.5, wallet=wallet)
    balance = wait_for(lambda: (b := client.call('blockchain.scripthash.get_balance', sh))['unconfirmed'] and b,
                       'the transaction to appear in the mempool of the server')
    assert balance == {'confirmed': 0, 'unconfirmed': 150_000_000}
    assert client.call('blockchain.scripthash.get_mempool', sh)[0]['tx_hash'] == txid

    # confirmed
    node.mine(1, miner)
    balance = wait_for(lambda: (b := client.call('blockchain.scripthash.get_balance', sh))['confirmed'] and b,
                       'the transaction to be confirmed')
    assert balance == {'confirmed': 150_000_000, 'unconfirmed': 0}
    history = client.call('blockchain.scripthash.get_history', sh)
    assert [h['tx_hash'] for h in history] == [txid]
    assert history[0]['height'] == node.call('getblockcount')

    # the raw transaction and its merkle proof (needs txindex on the node)
    raw = client.call('blockchain.transaction.get', txid)
    assert raw == node.call('getrawtransaction', txid)
    proof = client.call('blockchain.transaction.get_merkle', txid, history[0]['height'])
    assert proof['block_height'] == history[0]['height']

    # broadcast through the server
    other = node.call('getnewaddress', wallet=wallet)
    funded = node.call('fundrawtransaction', node.call('createrawtransaction', [], {other: 0.1}), wallet=wallet)
    signed = node.call('signrawtransactionwithwallet', funded['hex'], wallet=wallet)['hex']
    assert client.call('blockchain.transaction.broadcast', signed) == node.call('decoderawtransaction', signed)['txid']
