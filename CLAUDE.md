# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ElectrumX 2.0.x (PyPI/package name `e-x`, import name `electrumx`): an Electrum-protocol server (asyncio) that indexes a coin daemon (bitcoind-like) into a local DB (LevelDB or RocksDB). This repo is a fork meant to be adapted to a custom coin; upstream is `spesmilo/electrumx`. Keep changes localized (mainly `src/electrumx/lib/coins.py`) so upstream merges stay easy. MIT license: keep `LICENCE`.

## Commands

```bash
pip install -e ".[leveldb,rocksdb]"      # at least one DB engine extra is required; altcoin hash libs are extras too
pip install pytest pytest-asyncio pytest-cov pycodestyle

pytest                                   # all tests (what CI runs, with --cov=electrumx)
pytest tests/lib/test_coins.py           # single file
pytest tests/server/test_mempool.py::test_name   # single test
pycodestyle --max-line-length=140 src    # the only lint, enforced in CI
cd docs && make html                     # docs (Sphinx)

DB_ENGINE=rocksdb COIN=Bitcoin DB_DIRECTORY=... DAEMON_URL=http://user:pass@host:port/ electrumx_server
electrumx_rpc getinfo                    # talk to a running server via local RPC
```

Configuration is entirely via environment variables, parsed in `src/electrumx/server/env.py` (documented in `docs/environment.rst`). `DB_ENGINE` is mandatory in 2.0 (`leveldb` or `rocksdb`). Python >=3.10; free-threaded 3.14t is experimental.

## Architecture

Pipeline (see `docs/architecture.rst`): `Env` → `Controller` (`server/controller.py`) wires together `Daemon` (RPC client to the coin node, `server/daemon.py`), `BlockProcessor` (`block_processor.py`, indexes blocks/handles reorgs, writes via `db.py`/`history.py`/`storage.py`), `MemPool` (`mempool.py`), `SessionManager`/`ElectrumX` sessions (`session.py`, the only place that knows the Electrum wire protocol and its versions), and `PeerManager` (`peers.py`). `Notifications` in `controller.py` merges block and mempool "touched" hashXs/outpoints so clients are not notified twice.

Coin abstraction is the key extension point: `lib/coins.py` defines `Coin` and a large hierarchy of subclasses. A coin class selects behavior through class attributes: `DESERIALIZER` (block/tx format, in `lib/tx.py`, `tx_dash.py`, `tx_axe.py`), `DAEMON`, `BLOCK_PROCESSOR`, `SESSIONCLS`, address verbytes, `GENESIS_HASH`, `REORG_LIMIT`, `RPC_PORT`, `PEERS`, header handling, etc. Coins are discovered by walking `Coin` subclasses (`lookup_coin_class` matches `NAME` + `NET`), so a new coin is just a new subclass; non-final classes are abstract bases with `NET = None`. Concrete classes must define `TX_COUNT`, `TX_COUNT_HEIGHT`, `TX_PER_BLOCK` (used only for sync ETAs) or lookup raises.

Daemon requirements: for `COIN=Bitcoin`, Bitcoin Core >= 31 with `txindex=1` and `txospenderindex=1` is required (for `blockchain.outpoint.subscribe`); see `MIN_REQUIRED_DAEMON_VERSION` and `REQUIRED_DAEMON_INDEXES` on `Coin`. A custom coin on an older node must override these and the outpoint-subscribe path.

DB schema changed in 2.0 with no migration; changing on-disk format requires a full resync.

## Tests

`tests/lib` (coins, tx deserializers, hashes, scripts), `tests/server` (env, daemon, mempool, storage, API), plus fixture-driven `tests/test_blocks.py` / `test_transactions.py` using JSON files in `tests/blocks` and `tests/transactions` (add a fixture there when adding a coin with a custom deserializer).
