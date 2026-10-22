# plm-electrumx

```
Licence: MIT
Original Author: Neil Booth
Upstream Maintainers: The Electrum developers
Language: Python (>= 3.10)
```

`plm-electrumx` is an [Electrum](https://electrum.org) protocol server for Palladium (PLM), the coin of
[palladiumcore](https://github.com/palladium-coin/palladiumcore). It is a fork of
[spesmilo/electrumx](https://github.com/spesmilo/electrumx) that supports Palladium only.
It connects to your Palladium full node and indexes the blockchain, allowing efficient querying of
the history of arbitrary addresses.

## Running

### With Docker (next to the node of palladiumcore)

ElectrumX joins the `palladium` network created by the node in
[palladiumcore/docker](https://github.com/palladium-coin/palladiumcore/tree/docker-node/docker) and reaches it
as `palladiumd:2332`. RPC and ZMQ of the node are not published on the host, so nothing else is exposed.

1. Start the node (`docker compose up -d` in `palladiumcore/docker`). Its `~/.palladium/palladium.conf` needs
   `server=1` and `txindex=1` (no `prune`).
2. `cp .env.example .env` and set `PLM_RPC_USER` / `PLM_RPC_PASSWORD` to the RPC credentials of that file
   (use a dedicated `rpcauth` user for anything public).
3. `docker compose up -d --build`

The first start builds the database from the node from genesis, which takes a while; follow it with
`docker compose logs -f electrumx`. The database is the `electrumx-db` volume. Electrum clients connect to
TCP port 50001 (`ELECTRUMX_TCP_PORT` in `.env`). To announce a public server to the network, set
`REPORT_SERVICES` in `.env`. Settings are in `.env` and `docker-compose.yml`; the image defaults are in the
`Dockerfile`.

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

- Palladium Core is based on Bitcoin Core 0.19. It has no `getindexinfo`, `txospenderindex` or
  `submitpackage`, so the daemon version/index checks are disabled for `COIN=Palladium`, and
  `blockchain.outpoint.subscribe` and `blockchain.transaction.broadcast_package` return a daemon
  error to clients.
- The daemon must run with `txindex=1`.
- Same genesis blocks as Bitcoin (mainnet, testnet3, regtest), 80-byte headers, sha256d PoW, segwit.
- Parameters were taken from `src/chainparams.cpp` and `src/chainparamsbase.cpp` of palladiumcore.

## License

MIT, see `LICENCE`. The original copyright notices of ElectrumX are kept.
