# Fork notes

`plm-electrumx` is a fork of [spesmilo/electrumx](https://github.com/spesmilo/electrumx) adapted to
Palladium (PLM), the coin of [palladiumcore](https://github.com/palladium-coin/palladiumcore).

## Starting point

The first commit of this repository is an unmodified snapshot of upstream
[spesmilo/electrumx](https://github.com/spesmilo/electrumx) at commit
`280cb339aa158e099eb936033eecd15719770651`
("Merge pull request #389 from SomberNight/202607_release_2_0", upstream release 2.0.0, 3 July 2026).
The upstream history itself is not included. All Palladium-specific changes are in the commits after it:

    git log --reverse

## Updating from upstream

There is no common git history with upstream, so `git merge` does not work. Apply the upstream
changes since the snapshot as a patch instead:

    git remote add upstream https://github.com/spesmilo/electrumx.git   # once
    git fetch upstream
    git log 280cb33..upstream/master --oneline                          # what changed upstream
    git diff 280cb33 upstream/master | git apply --3way

Conflicts in files this fork deleted (see below) are resolved by keeping them deleted. After an update,
replace `280cb33` above with the new upstream commit that was applied.

## Removed from upstream

All other coins: their classes in `coins.py`, their transaction deserializers (`lib/tx.py`,
`tx_dash.py`, `tx_axe.py`), the session/daemon/block-processor subclasses only they used, their
tests and fixtures, and the altcoin pip extras. `Bitcoin` was folded into `Palladium`.
When merging upstream, resolve modify/delete conflicts on these files by keeping them deleted.

## Palladium specifics

- Palladium Core is based on Bitcoin Core 0.19. It has no `getindexinfo`, `txospenderindex` or
  `submitpackage`, so the daemon version/index checks are disabled for `COIN=Palladium`, and
  `blockchain.outpoint.subscribe` and `blockchain.transaction.broadcast_package` return a daemon
  error to clients.
- The daemon must run with `txindex=1`.
- Same genesis blocks as Bitcoin (mainnet, testnet3, regtest), 80-byte headers, sha256d PoW, segwit.
- Parameters were taken from `src/chainparams.cpp` and `src/chainparamsbase.cpp` of palladiumcore.
