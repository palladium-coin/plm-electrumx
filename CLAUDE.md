# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`plm-electrumx`: a fork of ElectrumX 2.0.0 with its own versioning (package name `plm-electrumx`, version in `src/electrumx/__init__.py` and `docs/conf.py`, import name `electrumx`), an Electrum-protocol server (asyncio) that indexes a coin daemon into a local DB (LevelDB or RocksDB), supporting **Palladium (PLM) only**. All other coins and their code were removed (see the "Fork notes" in `README.md` for the upstream base commit and how to merge upstream). Keep changes to core files small so upstream merges stay easy. MIT license: keep `LICENCE`.

## Commands

Always run tests, lint and installs in a Python virtual environment (`python3 -m venv venv && . venv/bin/activate`;
`/venv/` is in `.gitignore`), never with the system pip, also inside Docker containers used to run tests. RocksDB needs
RocksDB >= 8.0 for `rocksdb-ng`: Debian 12 ships 7.8.3, so on it test RocksDB in a `python:3.14-trixie` container
(RocksDB 9.10, set `ALLOW_ROOT=1` there because the server refuses to run as root).

```bash
pip install -e ".[leveldb,rocksdb]"      # at least one DB engine extra is required
pip install pytest pytest-asyncio pytest-cov pycodestyle

pytest                                   # all tests (what CI runs, with --cov=electrumx)
pytest tests/lib/test_palladium.py       # single file
pytest tests/server/test_mempool.py::test_name   # single test
pycodestyle --max-line-length=140 src    # the only lint, enforced in CI

cd docs && make html                     # docs (Sphinx)

# integration tests: ElectrumX against a real Palladium regtest node in Docker (skipped unless PLM_TEST_DAEMON_URL is set)
docker compose -f tests/integration/docker-compose.yml up -d --build --wait
PLM_TEST_DAEMON_URL=http://plmtest:plmtest@127.0.0.1:28443/ pytest tests/integration
docker compose -f tests/integration/docker-compose.yml down -v

DB_ENGINE=rocksdb DB_DIRECTORY=... DAEMON_URL=http://user:pass@host:port/ electrumx_server
electrumx_rpc getinfo                    # needs rpc:// in SERVICES (the Docker image does not enable it)
contrib/docker-smoke-test.sh             # after `docker build -t plm-electrumx .`: checks the SSL handling of the entrypoint
```

Docker: needs `.env` (copy `.env.example`; `PLM_RPC_USER`/`PLM_RPC_PASSWORD` are required, the rest has defaults) and the data directory created as your user first: `mkdir -p ~/.plm-electrumx/db ~/.plm-electrumx/ssl`. Then `docker compose up -d --build` (root `Dockerfile`, `docker-compose.yml`, `.env` from `.env.example`) runs the server on the external `palladium` network of the Palladium node container, daemon at `palladiumd:2332`. `docker-entrypoint.sh` sets up SSL: it uses `SSL_CERTFILE`/`SSL_KEYFILE` if given, else the self-signed certificate in `ssl/` of the data directory (`~/.plm-electrumx`, bind-mounted), generating it only if missing (never overwrite it: clients pin it), and sets `SERVICES`.

Do not run Python with `src/electrumx/lib/` as the current directory: `lib/enum.py` shadows the standard `enum` module and breaks the interpreter.

Configuration is entirely via environment variables, parsed in `src/electrumx/server/env.py` (documented in `docs/environment.rst`). `DB_ENGINE` is mandatory in 2.0 (`leveldb` or `rocksdb`). Python >=3.10; free-threaded 3.14t is experimental.

## Architecture

Pipeline (see `docs/architecture.rst`): `Env` → `Controller` (`server/controller.py`) wires together `Daemon` (RPC client to the coin node, `server/daemon.py`), `BlockProcessor` (`block_processor.py`, indexes blocks/handles reorgs, writes via `db.py`/`history.py`/`storage.py`), `MemPool` (`mempool.py`), `SessionManager`/`ElectrumX` sessions (`session.py`, the only place that knows the Electrum wire protocol and its versions), and `PeerManager` (`peers.py`). `Notifications` in `controller.py` merges block and mempool "touched" hashXs/outpoints so clients are not notified twice.

Coin abstraction: `lib/coins.py` defines `Coin` and the `Palladium`, `PalladiumTestnet`, `PalladiumRegtest` subclasses. A coin class selects behavior through class attributes: `DESERIALIZER` (block/tx format, in `lib/tx.py`, only the segwit one remains), `DAEMON`, `BLOCK_PROCESSOR`, `SESSIONCLS`, address verbytes, `GENESIS_HASH`, `REORG_LIMIT`, `RPC_PORT`, `PEERS`, header handling, etc. Coins are discovered by walking `Coin` subclasses (`lookup_coin_class` matches `NAME` + `NET`; `COIN` defaults to `Palladium`). Concrete classes must define `TX_COUNT`, `TX_COUNT_HEIGHT`, `TX_PER_BLOCK` (used only for sync ETAs) or lookup raises.

Daemon: Palladium Core has segwit and taproot (BIP341/342, mainnet height 405000; the server is script-type agnostic, indexing by script hash) and bech32/bech32m addresses, but no `getindexinfo`, `txospenderindex` or `submitpackage` RPCs. So `MIN_REQUIRED_DAEMON_VERSION`/`REQUIRED_DAEMON_INDEXES` (see `Coin`) are unset, and `blockchain.outpoint.subscribe` is refused with an explicit error (`Coin.DAEMON_HAS_TXO_SPENDER_INDEX = False`: otherwise the subscription is accepted and the daemon error at the next block closes the session) while `blockchain.transaction.broadcast_package` returns an explicit "not supported" error (the daemon answers method not found). The daemon needs `txindex=1`.

DB schema changed in 2.0 with no migration; changing on-disk format requires a full resync.

## Tests

Integration tests (`tests/integration`): `node/Dockerfile` + `node/palladium.conf` run the Palladium node (official release binaries, signature checked) in regtest, `conftest.py` starts `electrumx_server` on an empty DB against it and the tests mine blocks and check headers, balances, mempool, history, merkle proofs and broadcast through the Electrum protocol. Regtest coinbase maturity is 120 blocks, bech32 hrp is `rplm` (`plm` on mainnet, `tplm` on testnet: `Coin.BECH32_HRP`). The CI job is `integration` (LevelDB and RocksDB; `PLM_TEST_DB_ENGINE` selects the engine locally). Bump `VERSION` in the Dockerfile to test against a newer node.

`tests/lib` (Palladium params, addresses, hashes, scripts), `tests/server` (env, daemon, mempool, storage, API), plus fixture-driven `tests/test_blocks.py` / `test_transactions.py` using JSON files named `<coin>_<net>_<id>.json` in `tests/blocks` and `tests/transactions` (real mainnet data from a synced node; tx vout values in satoshis). `test_storage.py` needs both DB engines installed. Fixtures (including a taproot spend, `palladium_mainnet_2a74f4`) were taken from a synced node (`getblock <hash> 0|1`, `getrawtransaction <txid> true <blockhash>`, run via `docker compose exec palladiumd palladium-cli ...` in the node's project); vout values converted to satoshis. Ports, SSL, RPC credentials and donation address are documented in `DEPLOY.md`.

## Repository and workflow

- Default branch `main`, remotes `origin` (palladium-coin/plm-electrumx) and `upstream` (spesmilo/electrumx). With two remotes `gh` needs `--repo palladium-coin/plm-electrumx` (or `gh repo set-default`).
- History is a snapshot of upstream commit `280cb33` plus Palladium commits: no common history, `git merge upstream` does not work. Update with `git diff 280cb33 upstream/master | git apply --3way` (see the "Fork notes" in `README.md`).
- Do not create, move or delete git tags.
- Do not `git add -A`: generated files (`.coverage`, `.env`) get swept in. Add files by name. `.coverage` and `.env` are in `.gitignore`.
- CI (`.github/workflows/ci.yml`, on `main`): `unittests`, `pycodestyle`, `build_docs`, `docker` (builds the image, runs the smoke test). It runs on Ubuntu 24.04, amd64 and arm64 (`ubuntu-24.04-arm`) for `unittests`, `docker` and `integration`.
- In repo documentation never cite paths or links of the palladiumcore repository; describe the concept (the Palladium node, the `palladium` Docker network).
