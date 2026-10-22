# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`plm-electrumx`: a fork of ElectrumX 2.0.x (package name `e-x`, import name `electrumx`), an Electrum-protocol server (asyncio) that indexes a coin daemon into a local DB (LevelDB or RocksDB), supporting **Palladium (PLM) only**. All other coins and their code were removed (see the "Fork notes" in `README.md` for the upstream base commit and how to merge upstream). Keep changes to core files small so upstream merges stay easy. MIT license: keep `LICENCE`.

## Commands

```bash
pip install -e ".[leveldb,rocksdb]"      # at least one DB engine extra is required
pip install pytest pytest-asyncio pytest-cov pycodestyle

pytest                                   # all tests (what CI runs, with --cov=electrumx)
pytest tests/lib/test_coins.py           # single file
pytest tests/server/test_mempool.py::test_name   # single test
pycodestyle --max-line-length=140 src    # the only lint, enforced in CI
cd docs && make html                     # docs (Sphinx)

DB_ENGINE=rocksdb DB_DIRECTORY=... DAEMON_URL=http://user:pass@host:port/ electrumx_server
electrumx_rpc getinfo                    # talk to a running server via local RPC
```

Docker: `docker compose up -d --build` (root `Dockerfile`, `docker-compose.yml`, `.env` from `.env.example`) runs the server on the external `palladium` network of the node in palladiumcore/docker, daemon at `palladiumd:2332`.

Configuration is entirely via environment variables, parsed in `src/electrumx/server/env.py` (documented in `docs/environment.rst`). `DB_ENGINE` is mandatory in 2.0 (`leveldb` or `rocksdb`). Python >=3.10; free-threaded 3.14t is experimental.

## Architecture

Pipeline (see `docs/architecture.rst`): `Env` → `Controller` (`server/controller.py`) wires together `Daemon` (RPC client to the coin node, `server/daemon.py`), `BlockProcessor` (`block_processor.py`, indexes blocks/handles reorgs, writes via `db.py`/`history.py`/`storage.py`), `MemPool` (`mempool.py`), `SessionManager`/`ElectrumX` sessions (`session.py`, the only place that knows the Electrum wire protocol and its versions), and `PeerManager` (`peers.py`). `Notifications` in `controller.py` merges block and mempool "touched" hashXs/outpoints so clients are not notified twice.

Coin abstraction: `lib/coins.py` defines `Coin` and the `Palladium`, `PalladiumTestnet`, `PalladiumRegtest` subclasses. A coin class selects behavior through class attributes: `DESERIALIZER` (block/tx format, in `lib/tx.py`, only the segwit one remains), `DAEMON`, `BLOCK_PROCESSOR`, `SESSIONCLS`, address verbytes, `GENESIS_HASH`, `REORG_LIMIT`, `RPC_PORT`, `PEERS`, header handling, etc. Coins are discovered by walking `Coin` subclasses (`lookup_coin_class` matches `NAME` + `NET`; `COIN` defaults to `Palladium`). Concrete classes must define `TX_COUNT`, `TX_COUNT_HEIGHT`, `TX_PER_BLOCK` (used only for sync ETAs) or lookup raises.

Daemon: Palladium Core is based on Bitcoin Core 0.19: no `getindexinfo`, `txospenderindex` or `submitpackage`. So `MIN_REQUIRED_DAEMON_VERSION`/`REQUIRED_DAEMON_INDEXES` (see `Coin`) are unset, and `blockchain.outpoint.subscribe` / `blockchain.transaction.broadcast_package` return a daemon error to clients. The daemon needs `txindex=1`.

DB schema changed in 2.0 with no migration; changing on-disk format requires a full resync.

## Tests

`tests/lib` (Palladium params, addresses, hashes, scripts), `tests/server` (env, daemon, mempool, storage, API), plus fixture-driven `tests/test_blocks.py` / `test_transactions.py` using JSON files named `<coin>_<net>_<id>.json` in `tests/blocks` and `tests/transactions` (real mainnet data from a synced node; tx vout values in satoshis). `test_storage.py` needs both DB engines installed. Bech32 addresses are not supported by `Coin.address_to_hashX` (base58 only).
