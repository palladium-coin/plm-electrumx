'''Electrum protocol methods per protocol version, daemon limits and reorgs, against the regtest node (see conftest.py).'''
import pytest

import ssl

from tests.integration.conftest import SSL_SERVICE, ElectrumClient, new_address, scripthash, wait_for


@pytest.fixture
def client(electrumx):
    client = ElectrumClient(electrumx)
    yield client
    client.close()


def negotiate(client, version):
    return client.call('server.version', 'plm-integration-test', version)


def spk_of(node, address):
    return node.call('getaddressinfo', address)['scriptPubKey']


@pytest.mark.parametrize('version', ['1.4', '1.4.2', '1.5', '1.6', '1.7'])
def test_protocol_versions(client, version):
    assert negotiate(client, version)[1] == version


def test_unsupported_protocol_versions(electrumx):
    for version in ('1.3', '2.0'):
        client = ElectrumClient(electrumx)
        try:
            with pytest.raises(RuntimeError, match='unsupported protocol version'):
                negotiate(client, version)
        finally:
            client.close()


def test_server_features(node, client):
    negotiate(client, '1.4')
    features = client.call('server.features')
    assert features['genesis_hash'] == node.call('getblockhash', 0)
    assert features['hash_function'] == 'sha256'
    assert features['protocol_min'] == '1.4'


def test_relayfee_and_estimatefee(client):
    negotiate(client, '1.5')  # blockchain.relayfee was removed in 1.6
    assert client.call('blockchain.relayfee') > 0
    assert isinstance(client.call('blockchain.estimatefee', 2), (int, float))


def test_mempool_info(client):
    '''The daemon reports 'incrementalfee' in getnetworkinfo, not 'incrementalrelayfee' in getmempoolinfo'''
    negotiate(client, '1.6')
    info = client.call('mempool.get_info')
    assert set(info) == {'mempoolminfee', 'minrelaytxfee', 'incrementalrelayfee'}
    assert all(fee > 0 for fee in info.values())


def test_daemon_limits_are_reported_as_errors(client):
    '''The Palladium daemon has no submitpackage and no gettxspendingprevout: clients get an error.
    If a newer daemon gains them, update CLAUDE.md, README.md and DEPLOY.md and this test.'''
    negotiate(client, '1.7')
    with pytest.raises(RuntimeError, match='does not support package submission'):
        client.call('blockchain.transaction.broadcast_package', ['00'])
    # a subscription would be accepted for an outpoint in the mempool and then close the session at the next block
    with pytest.raises(RuntimeError, match='outpoint subscriptions are not supported'):
        client.call('blockchain.outpoint.subscribe', '00' * 32, 0, '')


def test_protocol_1_7_scriptpubkey_methods(node, wallet, client):
    negotiate(client, '1.7')
    target = node.call('getnewaddress', '', 'bech32m', wallet=wallet)
    spk = spk_of(node, target)
    txid = node.call('sendtoaddress', target, 2, wallet=wallet)
    wait_for(lambda: client.call('blockchain.scriptpubkey.get_mempool', spk)['history'], 'the tx in the mempool')
    assert txid in [h['tx_hash'] for h in client.call('blockchain.scriptpubkey.get_history', spk)['history']]
    assert client.call('blockchain.scriptpubkey.get_balance', spk)['unconfirmed'] == 200_000_000
    assert client.call('blockchain.scriptpubkey.subscribe', spk) is not None
    # mempool.recent lists it
    assert txid in [t['txid'] for t in client.call('mempool.recent')]
    node.mine(1, new_address(node, wallet))
    wait_for(lambda: client.call('blockchain.scriptpubkey.get_balance', spk)['confirmed'] == 200_000_000, 'confirmation')
    unspent = client.call('blockchain.scriptpubkey.listunspent', spk)['utxos']
    assert [(u['tx_hash'], u['value']) for u in unspent] == [(txid, 200_000_000)]
    assert client.call('blockchain.scriptpubkey.unsubscribe', spk) is True


def test_testmempoolaccept(node, wallet, client):
    negotiate(client, '1.7')
    target = new_address(node, wallet)
    funded = node.call('fundrawtransaction', node.call('createrawtransaction', [], {target: 0.1}), wallet=wallet)
    signed = node.call('signrawtransactionwithwallet', funded['hex'], wallet=wallet)['hex']
    result, = client.call('blockchain.transaction.testmempoolaccept', [signed])
    assert result['allowed'] is True


def test_reorg_replaces_blocks(node, wallet, electrumx, client):
    '''The server follows a reorg: the block is replaced by a longer chain that confirms the tx again.
    Like upstream ElectrumX it reorganises when the daemon's chain gets longer than its own, not before.'''
    negotiate(client, '1.4.2')
    miner = new_address(node, wallet)
    target = node.call('getnewaddress', '', 'bech32', wallet=wallet)
    sh = scripthash(node, target)
    txid = node.call('sendtoaddress', target, 1, wallet=wallet)
    block = node.mine(1, miner)[0]
    height = node.call('getblockcount')
    wait_for(lambda: client.call('blockchain.scripthash.get_balance', sh)['confirmed'] == 100_000_000, 'confirmation')
    old_header = client.call('blockchain.block.header', height)

    node.call('invalidateblock', block)
    new_blocks = node.mine(2, new_address(node, wallet))  # other coinbase, else the same block; the tx goes back to the mempool and is mined again in the first one
    assert block not in new_blocks
    wait_for(lambda: client.call('blockchain.headers.subscribe')['height'] == height + 1, 'the server to follow the new chain')
    assert client.call('blockchain.block.header', height) != old_header
    wait_for(lambda: client.call('blockchain.scripthash.get_balance', sh) == {'confirmed': 100_000_000, 'unconfirmed': 0},
             'the balance after the reorg')
    history = client.call('blockchain.scripthash.get_history', sh)
    assert [(h['tx_hash'], h['height']) for h in history] == [(txid, height)]


def test_ssl_service(node, electrumx):
    '''The SSL port serves the same protocol, with the certificate given by SSL_CERTFILE/SSL_KEYFILE'''
    context = ssl.create_default_context(cafile=SSL_SERVICE['certfile'])
    client = ElectrumClient(SSL_SERVICE['port'], context)
    try:
        assert negotiate(client, '1.4')[1] == '1.4'
        assert client.call('blockchain.block.header', 0)
    finally:
        client.close()
    # a client that does not trust the (self-signed) certificate refuses it
    with pytest.raises(ssl.SSLCertVerificationError):
        ElectrumClient(SSL_SERVICE['port'], ssl.create_default_context())
