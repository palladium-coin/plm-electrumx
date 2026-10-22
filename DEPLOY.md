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
| **50002/tcp** | Electrum protocol over SSL | clients | on by default, certificate generated automatically (see "SSL"); published by `docker-compose.yml` |
| **2333/tcp** | Palladium P2P (the node) | the internet, inbound | published by the node's compose file |
| 2332/tcp | node RPC | **only the `palladium` network** | never publish or forward it: it can spend wallet funds |
| 28332, 28334, 28335/tcp | node ZMQ | only the `palladium` network | never publish or forward them |

Changing the published ports: `ELECTRUMX_TCP_PORT` / `ELECTRUMX_SSL_PORT` in `.env` (host side only; the container always listens on 50001).

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

SSL is **on by default** and needs nothing to be set up: Electrum wallets prefer it, and plain TCP (50001) sends
addresses and balances unencrypted.

### What happens at start

`docker-entrypoint.sh` (the entrypoint of the image) does this at every start:

1. If you gave your own certificate (`SSL_CERTFILE` and `SSL_KEYFILE`, see below), it uses that.
2. Otherwise it looks for `server.crt` and `server.key` in `~/.plm-electrumx/ssl` (`/var/lib/electrumx-ssl` in the container).
   - **They exist: they are used as they are, never overwritten.**
   - **They do not exist (first start): a self-signed certificate valid 10 years is generated** for `SSL_HOSTNAME`
     and saved there. If only one of the two files exists, the container stops with an error instead of overwriting it.
3. It prints the certificate subject, expiry date and SHA-256 fingerprint in the log
   (`docker compose logs electrumx | grep entrypoint`), and warns if it expires in less than 30 days.
4. If `SERVICES` is not set, it sets it to `tcp://:50001,ssl://:50002`.

The compose file publishes 50002 (`ELECTRUMX_SSL_PORT`). Settings, all in `.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `SSL_ENABLED` | `true` | `false`: no SSL, only `tcp://:50001` |
| `SSL_HOSTNAME` | `electrumx` | name (or IP) written in a generated certificate; set it to the name of the server (it matters only when the certificate is generated) |
| `SSL_CERTFILE`, `SSL_KEYFILE` | unset | your own certificate and key (paths inside the container); both or neither |
| `ELECTRUMX_SSL_PORT` | `50002` | host port published for SSL |

### Self-signed certificate: what clients see

A generated certificate is signed by nobody. Electrum wallets handle it by *trust on first use*: at the first connection
the wallet saves the certificate, and from then on it refuses a different one (as SSH does with host keys), so a
man-in-the-middle cannot take over later. The fields of the certificate (name, country, ...) are not checked by the
client, only the expiry date. Consequences:

- **Keep the certificate.** It is in `~/.plm-electrumx/ssl`, separate from the database (`~/.plm-electrumx/db`) on
  purpose: the database can be deleted and rebuilt at any time, the certificate should not be. If `ssl/` is deleted,
  a new certificate is generated and every client that saved the old one refuses to connect.
- **Back it up** by copying the folder (it contains the private key: keep it private):
  ```bash
  cp -a ~/.plm-electrumx/ssl /safe/place/plm-electrumx-ssl
  ```
  To restore it, copy the two files (`server.crt`, `server.key`) back into `~/.plm-electrumx/ssl` before the first
  start, or use them as "your own certificate" below.
- If it expires or is lost, clients that saved it must be told to forget it, or the server must get a new name.
  Generated certificates last 10 years, so expiry is rarely the problem.
- Whether a wallet accepts a self-signed certificate depends on the wallet. Electrum does (trust on first use);
  check the wallet you intend to use.

### Your own certificate (for example Let's Encrypt)

With a certificate signed by a CA the client verifies it by itself, with no trust on first use, but it needs a domain
and must be renewed (about every 90 days).

1. Get the certificate and key (`certbot certonly --standalone -d electrum.example.com`).
   Copy the files out of `/etc/letsencrypt/live/...` (they are symlinks into `archive/`) to a folder, and copy them
   again after each renewal. The container runs as uid 1000, so the key must be readable by it
   (`chown 1000 privkey.pem && chmod 600 privkey.pem`).
2. Mount the folder with a `docker-compose.override.yml` next to `docker-compose.yml` (compose reads it automatically):
   ```yaml
   services:
     electrumx:
       volumes:
         - /path/to/certs:/certs:ro
   ```
3. In `.env`:
   ```ini
   SSL_CERTFILE=/certs/fullchain.pem
   SSL_KEYFILE=/certs/privkey.pem
   ```
4. `docker compose up -d`. After a renewal, `docker compose restart electrumx` loads the new files.

If the files cannot be read, the container stops with a message that says so (see `docker compose logs electrumx`).

### Check it

```bash
echo | openssl s_client -connect 127.0.0.1:50002 2>/dev/null | openssl x509 -noout -subject -enddate -fingerprint -sha256
printf '{"id":1,"method":"server.version","params":["test","1.4"]}\n' | openssl s_client -quiet -connect 127.0.0.1:50002
```

The fingerprint must be the one printed in the log. Open 50002 as in "Ports" for a public server.

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

## Donation address

`DONATION_ADDRESS` in `.env` sets the address the server reports to its clients. It is optional and empty by default
(no address).

```ini
DONATION_ADDRESS=plm1q...your address...
```

- Clients get it with the Electrum protocol call `server.donation_address`; wallets that support it show it to the user.
- A banner file (`BANNER_FILE`, see `docs/environment.rst`) can contain the placeholder `$DONATION_ADDRESS`, which is
  replaced with this address.
- The server does **not** check the value, it only passes it on. Check it carefully (for example send a small test
  amount) and use an address you are happy to make public, since it is sent to everyone who connects.
- After changing it, apply it with `docker compose up -d` (the container is recreated with the new value).

## Data directory and first start

Create the data directory as the user that runs Docker, before the first start (otherwise Docker creates it as root and
the container cannot write; the log then says `ERROR: ... is not writable`):

```bash
mkdir -p ~/.plm-electrumx/db ~/.plm-electrumx/ssl
```

The container runs as uid/gid 1000 (the first user of most hosts). For another user set `PLM_UID` / `PLM_GID` in `.env`.
To keep the data elsewhere, set `ELECTRUMX_DATADIR` in `.env`.

- On the first start ElectrumX builds its database from the node, from genesis. With the chain at about 542,000 blocks
  it took roughly a minute on a development machine, ending at about 230 MB of database and 0.5 GB of RAM.
  The database grows with the chain.
- `CACHE_MB` in `.env` is the memory used for caching during the sync (default in `docker-compose.yml`: 1200).
- The data directory is `~/.plm-electrumx` (`ELECTRUMX_DATADIR`): `db/` is the database, `ssl/` the certificate.
  The database is derived from the node, so it can be rebuilt at any time: stop the container, delete `db/` and start
  again (it syncs again). A backup of it is optional; keep a backup of `ssl/`.
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
| container stops at once, log says `ERROR: ... is not writable` | the data directory belongs to another user (or to root, if Docker created it): `chown -R $(id -u):$(id -g) ~/.plm-electrumx`, or set `PLM_UID`/`PLM_GID` |
| container restarts at once, log says `ERROR: ... SSL_CERTFILE` | your own certificate is not mounted or not readable by uid 1000, only one of `SSL_CERTFILE`/`SSL_KEYFILE` is set, or only one of the generated files exists in `~/.plm-electrumx/ssl` |
| a wallet refuses the server after it worked | the certificate changed (for example `ssl/` was deleted); the wallet saved the old one |
