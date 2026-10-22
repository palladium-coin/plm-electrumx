# Deploying plm-electrumx

What to set up to run a Palladium Electrum server with Docker, next to the Palladium node
running in Docker (service `palladiumd` on the Docker network `palladium`).
Quick start is in [README.md](README.md); this file covers ports, security and operation.

## Overview

```
Electrum clients ──50001 (tcp) / 50002 (ssl)──▶ electrumx ──palladiumd:2332 (RPC)──▶ palladiumd ◀── 2333 ──▶ Palladium network
                                                  container   private "palladium" network   container
```

The node and ElectrumX talk over the private Docker network `palladium`. The only things that must be
reachable from outside are the node's P2P port and the Electrum port(s) of this server.

## Node requirements

In `~/.palladium/palladium.conf` (restart the node container after a change):

```ini
server=1
txindex=1          # required: ElectrumX looks up any transaction by id
# prune must NOT be set: ElectrumX reads the whole chain
```

Start the node **before** ElectrumX: it creates the `palladium` network, which `docker-compose.yml` declares
as `external`. If the network is missing, `docker compose up` fails with `network palladium declared as external,
but could not be found`.

## RPC credentials

ElectrumX logs in to the node with `PLM_RPC_USER` / `PLM_RPC_PASSWORD` from `.env`. The defaults written by the node
(`rpcuser=username`) are only fine to try it. For a real server create a user of its own with
the `rpcauth.py` helper that comes with Bitcoin Core-based nodes (Palladium Core included):

```bash
python3 rpcauth.py electrumx                     # prints the rpcauth= line and the password (shown once)
```

Put the `rpcauth=...` line in `palladium.conf` (and remove `rpcuser`/`rpcpassword`), restart the node, and put the
user and password in `.env`. Anything on the `palladium` network can try to log in, so use a long password.
Keep `.env` private (`chmod 600 .env`); it is ignored by git.

## Ports

| Port | What | Open to | Notes |
| --- | --- | --- | --- |
| **50001/tcp** | Electrum protocol, plain | clients (internet, if the server is public) | published by `docker-compose.yml` |
| **50002/tcp** | Electrum protocol over SSL | clients | optional, needs a certificate (see below); not published by default |
| **2333/tcp** | Palladium P2P (the node) | the internet, inbound | published by the node's compose file |
| 2332/tcp | node RPC | **only the `palladium` network** | never publish or forward it: it can spend wallet funds |
| 28332, 28334, 28335/tcp | node ZMQ | only the `palladium` network | never publish or forward them |

Changing the published port: `ELECTRUMX_TCP_PORT` in `.env` (host side only; the container always listens on 50001).

A server only for yourself (or for other containers) needs no open port: connect to `127.0.0.1:50001`, or join the
`palladium` network and use `electrumx:50001`.

### Firewall

- Docker publishes `ports:` by writing its own firewall rules, which **bypass `ufw` and `firewalld`**. A published
  port is open to the internet even if `ufw` denies it. To keep a port private, bind it to an address, for example
  `"127.0.0.1:50001:50001"` in `docker-compose.yml`.
- For a public server, allow what you want reachable: `sudo ufw allow 2333/tcp` (node) and the Electrum port(s).
  Since Docker bypasses ufw for published ports, this matters mostly for services not run by Docker.

### Router (server behind NAT)

Give the server a fixed LAN address (DHCP reservation) and forward to it:

| External port | Protocol | To | Needed for |
| --- | --- | --- | --- |
| 2333 | TCP | `<server LAN IP>:2333` | the node (optional but recommended: more peers) |
| 50001 | TCP | `<server LAN IP>:50001` | a public Electrum server |
| 50002 | TCP | `<server LAN IP>:50002` | a public Electrum server with SSL |

Never forward 2332 or 28332/28334/28335. A server on a VPS with a public IP opens the ports in the provider's firewall instead.

## SSL (port 50002)

Most Electrum wallets prefer SSL. You need a certificate and key for the host name of the server.

1. Get a certificate, for example with Let's Encrypt (`certbot certonly --standalone -d electrum.example.com`),
   or a self-signed one for tests:
   ```bash
   openssl req -x509 -newkey rsa:4096 -nodes -days 3650 -subj "/CN=electrum.example.com" \
     -keyout privkey.pem -out fullchain.pem
   ```
2. Create `docker-compose.override.yml` next to `docker-compose.yml` (compose reads it automatically):
   ```yaml
   services:
     electrumx:
       environment:
         SERVICES: tcp://:50001,ssl://:50002
         SSL_CERTFILE: /certs/fullchain.pem
         SSL_KEYFILE: /certs/privkey.pem
       ports:
         - "50002:50002"
       volumes:
         - /path/to/certs:/certs:ro
   ```
   The container runs as uid 1000: the key must be readable by it (`chown 1000 privkey.pem; chmod 600 privkey.pem`).
   With Let's Encrypt, copy the files out of `/etc/letsencrypt/live/...` (they are symlinks into `archive/`), and
   copy them again after each renewal.
3. `docker compose up -d`, and open 50002 as in "Ports".

## Announcing a public server

`REPORT_SERVICES` in `.env` is the address other servers and clients are told to use. Set it only for a server that is
reachable from outside, with its public host name (not an IP on a private network, not `localhost`):

```ini
REPORT_SERVICES=tcp://electrum.example.com:50001,ssl://electrum.example.com:50002
```

Peer discovery is on by default (`PEER_DISCOVERY`, `PEER_ANNOUNCE`). `lib/coins.py` has no known Palladium servers yet
(`PEERS = []` in the `Palladium` class), so a new server has nobody to learn the network from. Add the
servers you know there (format: `'host s t'`, for example `'electrum.example.com s50002 t50001'`) and rebuild, or
keep the server private with `PEER_DISCOVERY=off` / `PEER_DISCOVERY=self`.

## Resources and first start

- On the first start ElectrumX builds its database from the node, from genesis. With the chain at about 542,000 blocks
  it took roughly a minute on a development machine, ending at about 230 MB of database and 0.5 GB of RAM.
  The database grows with the chain.
- `CACHE_MB` in `.env` is the memory used for caching during the sync (default in `docker-compose.yml`: 1200).
- The database is the `electrumx-db` volume. It is derived from the node, so it can be rebuilt at any time:
  `docker compose down -v` deletes it and the next start syncs again. A backup is optional.
- Disk: the node needs `txindex`, so budget for the node's own data too (see the node's README).

## Operation

```bash
docker compose up -d --build        # start / update after pulling changes
docker compose logs -f electrumx    # follow the log
docker compose ps
docker compose stop                 # clean shutdown (up to 2 minutes to flush the db)
```

Is it up and synced? The log should end with `synced to height <N>` and the same height as the node
(`docker compose exec palladiumd palladium-cli getblockcount` in the node's compose project).
From the host, a protocol check:

```bash
printf '{"id":1,"method":"server.version","params":["test","1.4"]}\n' | nc -q1 127.0.0.1 50001
```

From another machine, `nc -zv <public IP> 50001` must succeed if the server is meant to be public, and
`nc -zv <public IP> 2332` must fail.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `network palladium declared as external, but could not be found` | the node is not running (or its compose file was not started yet) |
| log: connection refused / cannot connect to `palladiumd:2332` | the node is stopped or still starting; check that the node container is running |
| log: `401`/authorization errors | wrong `PLM_RPC_USER` / `PLM_RPC_PASSWORD` in `.env`; the credentials must be the ones in the node's `palladium.conf` |
| errors mentioning `txindex` | `txindex=1` is missing in `palladium.conf` (an index added later is built while the node runs, which takes time) |
| `blockchain.outpoint.subscribe` or package broadcast return a daemon error | expected: Palladium Core is based on Bitcoin Core 0.19 and does not have these RPCs |
| the server stays at an old height | the node is not synced; ElectrumX only follows the node |
| clients cannot connect from outside | port not published/forwarded, firewall, or `SERVICES` does not list that protocol |
