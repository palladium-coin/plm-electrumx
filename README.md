# ElectrumX with Palladium (PLM) Support

This repository provides a **Dockerized** setup of **ElectrumX** with support for the **Palladium (PLM)** coin.
It also includes a test script (`test-server.py`) to verify the connection and main functionalities of the ElectrumX server.

Tested on:

* ✅ Debian 12
* ✅ Ubuntu 24.04

🔗 Palladium Full Node: [davide3011/palladiumcore](https://github.com/davide3011/palladiumcore)

---

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Electrum      │    │   ElectrumX     │    │   Palladium     │
│   Clients       │◄──►│   Server        │◄──►│   Full Node     │
│                 │    │   (Docker)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Requirements

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)
* Python 3.10+ (to use `test-server.py`)
* A running **Palladium** full node ([NotRin7/Palladium](https://github.com/NotRin7/Palladium))

**System Architecture**: This server requires a **64-bit system** (both AMD64 and ARM64 architectures are supported, but 32-bit systems are not compatible).

**Recommendation**: to ensure maximum stability and reduce communication latency, it is strongly recommended to run the Palladium node **on the same machine** that hosts the ElectrumX container.

---

## Docker Installation

If you don't have Docker installed yet, follow the official guide:
- [Install Docker](https://docs.docker.com/get-docker/)

For Docker Compose:
- [Install Docker Compose](https://docs.docker.com/compose/install/)

---

## Palladium Node Configuration

Before running ElectrumX, you need to configure your Palladium Core node to accept RPC connections. Edit your `palladium.conf` file (usually located in `~/.palladium/palladium.conf` on Linux/Mac or `%APPDATA%\Palladium\palladium.conf` on Windows).

### Recommended palladium.conf for Mainnet

```conf
# Server mode (required for RPC)
server=1

# RPC credentials (change these!)
rpcuser=<rpcuser>
rpcpassword=<rpcpassword>

# RPC port (default for mainnet)
rpcport=2332

# Allow Docker containers to connect (REQUIRED for ElectrumX)
# This setting allows RPC connections from all Docker networks
rpcbind=0.0.0.0
rpcallowip=127.0.0.1
rpcallowip=172.16.0.0/12

# Optional: reduce debug log verbosity
printtoconsole=0
```

**Important Notes:**
- **`rpcbind=0.0.0.0`**: Makes the RPC server listen on all network interfaces (not just localhost)
- **`rpcallowip=172.16.0.0/12`**: Allows connections from **all** Docker networks (covers 172.16.x.x through 172.31.x.x)
  - Docker containers run in isolated networks that can vary (172.17.x.x, 172.18.x.x, 172.21.x.x, etc.)
  - The `/12` subnet covers all possible Docker bridge networks, making this configuration universal
  - Without this setting, ElectrumX won't be able to connect to your Palladium node
- **Security**: These settings only allow local Docker containers to connect, not external machines
- **Change the credentials**: Never use default usernames/passwords in production

After editing `palladium.conf`, restart your Palladium Core node for the changes to take effect.

---

## ElectrumX Configuration

In the `docker-compose.yml` file, you can set the RPC credentials of the Palladium full node that ElectrumX will use:

```yaml
environment:
  DAEMON_URL: "http://<rpcuser>:<rpcpassword>@host.docker.internal:<port>/"
```

Replace with your actual values:

* `<rpcuser>` → RPC username of the node
* `<rpcpassword>` → RPC password of the node
* `<port>` → RPC port of the node (`2332` for mainnet, `12332` for testnet)

**Note:** The compose uses `host.docker.internal` to connect to the Palladium node running on your host machine (outside the container). This works on both Windows/Mac and Linux thanks to the `extra_hosts` configuration.

**Ports:** ElectrumX exposes:
- `50001` → TCP (unencrypted)
- `50002` → SSL (encrypted, recommended)

**Important:** never include real credentials in files you upload to GitHub.

---

## Network Support (Mainnet & Testnet)

This ElectrumX server supports both **Palladium mainnet** and **testnet**. You can switch between networks by modifying the `docker-compose.yml` configuration.

### Network Comparison

| Network | COIN Value | NET Value | RPC Port | Bech32 Prefix | Address Prefix |
|---------|-----------|-----------|----------|---------------|----------------|
| **Mainnet** | `Palladium` | `mainnet` | `2332` | `plm` | Standard (starts with `1` or `3`) |
| **Testnet** | `Palladium` | `testnet` | `12332` | `tplm` | Testnet (starts with `t`) |

---

### Running on Mainnet (Default)

The default configuration is set for **mainnet**. No changes are needed if you want to run on mainnet.

**Configuration in `docker-compose.yml`:**
```yaml
environment:
  COIN: "Palladium"
  NET: "mainnet"
  DAEMON_URL: "http://<rpcuser>:<rpcpassword>@host.docker.internal:2332/"
```

**Requirements:**
- Palladium Core node running on **mainnet**
- RPC port: `2332`
- RPC credentials configured in `palladium.conf`

---

### Switching to Testnet

To run ElectrumX on **testnet**, follow these steps:

#### Step 1: Configure Palladium Core for Testnet

Edit your Palladium Core configuration file (`palladium.conf`):

```conf
# Enable testnet
testnet=1

# Server mode (required for RPC)
server=1

# RPC credentials (change these!)
rpcuser=your_rpc_username
rpcpassword=your_secure_rpc_password

# RPC port for testnet
rpcport=12332

# Allow Docker containers to connect (REQUIRED for ElectrumX)
rpcbind=0.0.0.0
rpcallowip=127.0.0.1
rpcallowip=172.16.0.0/12
```

**Important:** The `rpcbind` and `rpcallowip` settings are **required** for Docker connectivity on all platforms. Without these, ElectrumX won't be able to connect to your Palladium node from inside the Docker container.

Restart your Palladium Core node to apply testnet configuration.

#### Step 2: Modify docker-compose.yml

Open `docker-compose.yml` and change these two values in the `environment` section:

**Before (Mainnet):**
```yaml
environment:
  COIN: "Palladium"
  NET: "mainnet"
  DAEMON_URL: "http://<rpcuser>:<rpcpassword>@host.docker.internal:2332/"
```

**After (Testnet):**
```yaml
environment:
  COIN: "Palladium"
  NET: "testnet"
  DAEMON_URL: "http://<rpcuser>:<rpcpassword>@host.docker.internal:12332/"
```

**Important changes:**
1. Change `NET` from `"mainnet"` to `"testnet"`
2. Change port in `DAEMON_URL` from `2332` to `12332`
3. Replace `<rpcuser>` and `<rpcpassword>` with your actual testnet RPC credentials

#### Step 3: Clear Existing Database (Important!)

When switching networks, you **must** clear the ElectrumX database to avoid conflicts:

```bash
# Stop the container
docker compose down

# Remove the database
rm -rf ./data/*

# Or on Windows:
# rmdir /s /q data
# mkdir data
```

#### Step 4: Rebuild and Restart

```bash
# Rebuild and start the container
docker compose up -d --build

# Monitor the logs
docker compose logs -f
```

The ElectrumX server will now sync with the Palladium **testnet** blockchain.

---

### Testnet-Specific Information

**Genesis Block Hash (Testnet):**
```
000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943
```

**Address Examples:**
- Legacy (P2PKH): starts with `t` (e.g., `tPLMAddress123...`)
- SegWit (Bech32): starts with `tplm` (e.g., `tplm1q...`)

**Network Ports:**
- Palladium Core RPC: `12332`
- Palladium Core P2P: `12333`
- ElectrumX TCP: `50001` (same as mainnet)
- ElectrumX SSL: `50002` (same as mainnet)

---

### Switching Back to Mainnet

To switch back from testnet to mainnet:

1. Edit `palladium.conf` and remove or comment `testnet=1`
2. Change `rpcport=2332` in `palladium.conf`
3. Restart Palladium Core node
4. In `docker-compose.yml`, change:
   - `NET: "testnet"` → `NET: "mainnet"`
   - Port in `DAEMON_URL` from `12332` → `2332`
5. Clear database: `rm -rf ./data/*`
6. Restart ElectrumX: `docker compose down && docker compose up -d`

---

## Build and Start the Project

1. Navigate to the directory containing `docker-compose.yml` and `Dockerfile`.

2. Start the containers with Docker Compose (builds the image automatically on first run):

   ```bash
   docker compose up -d
   ```

   **Note:** Docker Compose will automatically build the image if it doesn't exist. No need to run `docker build` manually!

3. Check the logs to verify that ElectrumX started correctly:

   ```bash
   docker compose logs -f
   ```

### Manual Build (Optional)

If you want to manually rebuild the Docker image (e.g., after code changes):

```bash
# Rebuild the image
docker compose build

# Or rebuild and restart in one command
docker compose up -d --build
```
---

## Testing with `test-server.py`

The `test-server.py` script allows you to connect to the ElectrumX server and test its APIs.

Usage example:

```bash
python test-server.py 127.0.0.1:50002
```

The script will perform:

* Handshake (`server.version`)
* Feature request (`server.features`)
* Block header subscription (`blockchain.headers.subscribe`)

---

## Notes

* `coins_plm.py` defines both **Palladium (PLM)** mainnet and **PalladiumTestnet** classes
* See "Network Support" section for switching between mainnet and testnet
* Production recommendations:

  * Protect RPC credentials
  * Use valid SSL certificates
  * Monitor containers (logs, metrics, alerts)

---

## License

Distributed under the **MIT** license. See the `LICENSE` file for details.
