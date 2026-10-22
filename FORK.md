# Fork notes

`plm-electrumx` is a fork of [spesmilo/electrumx](https://github.com/spesmilo/electrumx) adapted to
Palladium (PLM), the coin of [palladiumcore](https://github.com/palladium-coin/palladiumcore).

## Starting point

- Upstream commit: `280cb339aa158e099eb936033eecd15719770651`
  ("Merge pull request #389 from SomberNight/202607_release_2_0", upstream release 2.0.0, 3 July 2026)

Every commit up to and including that one is unmodified upstream history. All Palladium-specific
changes are made in the commits after it:

    git log 280cb33..main

## Updating from upstream

    git remote add upstream https://github.com/spesmilo/electrumx.git   # once
    git config rerere.enabled true
    git fetch upstream
    git log main..upstream/master --oneline
    git merge upstream/master

Palladium changes are kept small and localized (mainly the `Palladium*` classes at the end of
`src/electrumx/lib/coins.py`) to keep these merges easy.

## Palladium specifics

- Palladium Core is based on Bitcoin Core 0.19. It has no `getindexinfo`, `txospenderindex` or
  `submitpackage`, so the daemon version/index checks are disabled for `COIN=Palladium`, and
  `blockchain.outpoint.subscribe` and `blockchain.transaction.broadcast_package` return a daemon
  error to clients.
- The daemon must run with `txindex=1`.
- Same genesis blocks as Bitcoin (mainnet, testnet3, regtest), 80-byte headers, sha256d PoW, segwit.
- Parameters were taken from `src/chainparams.cpp` and `src/chainparamsbase.cpp` of palladiumcore.
