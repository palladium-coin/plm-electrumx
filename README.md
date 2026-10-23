# plm-electrumx

```
Licence: MIT
Maintainer (plm-electrumx): Davide Grilli
Original Author: Neil Booth
Upstream Maintainers: The Electrum developers
Language: Python (>= 3.10)
```

`plm-electrumx` is an [Electrum](https://electrum.org) protocol server for Palladium (PLM), the coin of
Palladium Core. It is a fork of
[spesmilo/electrumx](https://github.com/spesmilo/electrumx) that supports Palladium only.
It connects to your Palladium full node and indexes the blockchain, allowing efficient querying of
the history of arbitrary addresses.

## Running

### With Docker (next to the Palladium node)

ElectrumX joins the Docker network `palladium`, created by the node's compose project, and reaches the node
as `palladiumd:2332`. RPC and ZMQ of the node are not published on the host, so nothing else is exposed.

1. Start the node (a compose service named `palladiumd` on the network `palladium`). Its `~/.palladium/palladium.conf` needs
   `server=1` and `txindex=1` (no `prune`).
2. `cp .env.example .env` and set `PLM_RPC_USER` / `PLM_RPC_PASSWORD` to the RPC credentials of that file
   (use a dedicated `rpcauth` user for anything public).
3. Create the data directory as your user: `mkdir -p ~/.plm-electrumx/db ~/.plm-electrumx/ssl`
   (`ELECTRUMX_DATADIR` in `.env` changes it). The container runs as uid/gid 1000; for another user set
   `PLM_UID` / `PLM_GID` in `.env`.
4. `docker compose up -d --build`

The first start builds the database from the node from genesis, which takes a while; follow it with
`docker compose logs -f electrumx`. The data directory has `db/` (the database, rebuilt from the node if deleted) and `ssl/` (the certificate). Electrum clients connect to
TCP port 50001 (`ELECTRUMX_TCP_PORT` in `.env`) and SSL port 50002 (`ELECTRUMX_SSL_PORT`). SSL is on by default:
a self-signed certificate is generated on the first start, kept in `~/.plm-electrumx/ssl` and reused on every
later start (or use your own, see [DEPLOY.md](DEPLOY.md)). To announce a public server to the network, set
`REPORT_SERVICES` in `.env`. Settings are in `.env` and `docker-compose.yml`; the image defaults are in the
`Dockerfile`. Ports, firewall, SSL, RPC credentials and troubleshooting are in [DEPLOY.md](DEPLOY.md).

### Without Docker

Requirements: Python >= 3.10, a synced Palladium node with `server=1` and `txindex=1` (no pruning),
and one of the DB engines (`pip install ".[leveldb]"` or `pip install ".[rocksdb]"`).

    pip install ".[rocksdb]"
    DB_ENGINE=rocksdb DB_DIRECTORY=/path/to/db \
    DAEMON_URL=http://rpcuser:rpcpassword@127.0.0.1:2332/ \
    SERVICES=tcp://:50001 electrumx_server

`COIN` defaults to `Palladium` and `NET` to `mainnet` (`testnet` and `regtest` are also available).
All settings are environment variables, documented in `docs/environment.rst`; `docs/HOWTO.rst`
describes a full installation.

## Fork notes

### Starting point

The first commit of this repository is an unmodified snapshot of upstream
[spesmilo/electrumx](https://github.com/spesmilo/electrumx) at commit
`280cb339aa158e099eb936033eecd15719770651`
("Merge pull request #389 from SomberNight/202607_release_2_0", upstream release 2.0.0, 3 July 2026).
The upstream history itself is not included. All Palladium-specific changes are in the commits after it:

    git log --reverse

### Updating from upstream

There is no common git history with upstream, so `git merge` does not work. Apply the upstream
changes since the snapshot as a patch instead:

    git remote add upstream https://github.com/spesmilo/electrumx.git   # once
    git fetch upstream
    git log 280cb33..upstream/master --oneline                          # what changed upstream
    git diff 280cb33 upstream/master | git apply --3way

Conflicts in files this fork deleted (see below) are resolved by keeping them deleted. After an update,
replace `280cb33` above with the new upstream commit that was applied.

### Removed from upstream

All other coins: their classes in `coins.py`, their transaction deserializers (`lib/tx.py`,
`tx_dash.py`, `tx_axe.py`), the session/daemon/block-processor subclasses only they used, their
tests and fixtures, and the altcoin pip extras. `Bitcoin` was folded into `Palladium`.
When merging upstream, resolve modify/delete conflicts on these files by keeping them deleted.

### Palladium specifics

- Segwit and taproot (BIP341/342, active on mainnet from block 405000) are supported: the server indexes
  by the hash of the output script, so every script type is handled alike. Addresses (base58, bech32 `plm1`,
  bech32m for taproot) are only read by the local `electrumx_rpc query` command.
- Palladium Core has no `getindexinfo`, `txospenderindex` (`gettxspendingprevout`) or `submitpackage` RPCs,
  so the daemon version/index checks are disabled for `COIN=Palladium`, and
  `blockchain.outpoint.subscribe` is refused with an explicit error (`Coin.DAEMON_HAS_TXO_SPENDER_INDEX`)
  and `blockchain.transaction.broadcast_package` returns the daemon error to clients.
- The daemon must run with `txindex=1`.
- Same genesis blocks as Bitcoin (mainnet, testnet3, regtest), 80-byte headers, sha256d PoW.
- Parameters (address prefixes, ports, genesis hashes) were taken from the Palladium Core chain parameters.

## License

MIT, see `LICENCE`. The original copyright notices of ElectrumX are kept.
