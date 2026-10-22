RPC Interface
=============

You can query the status of a running server, and affect its behaviour
by sending **JSON RPC** commands to the LocalRPC port it is listening
on.  This is best done using the :file:`electrumx_rpc` script
provided.

The general form of invocation is::

  electrumx_rpc [-p PORT] <command> [arg1 [arg2...]]

The port to send the commands to can be specified on the command line,
otherwise the environment variable :envvar:`RPC_PORT` is used, and if
that is not set then **8000** is assumed.

The following commands are available:

add_peer
--------

Add a peer to the peers list.  ElectrumX will schedule an immediate
connection attempt.  This command takes a single argument: the peer's
"real name" as it used to advertise itself on IRC::

  $ electrumx_rpc add_peer "ecdsa.net v1.0 s110 t"
  "peer 'ecdsa.net v1.0 s110 t' added"

daemon_url
----------

This command takes an optional argument that is interpreted
identically to the :envvar:`DAEMON_URL` environment variable.  If
omitted, the default argument value is the process's existing
:envvar:`DAEMON_URL` environment variable.

This command replaces the daemon's URL at run-time, and also
forcefully rotates to the first URL in the list.

For example, in case ElectrumX has previously failed over to a
secondary daemon and you want to revert to the primary having resolved
the connectivity issue, invoking this command without an argument will
have that effect.

disconnect
----------

Disconnect the given session IDs or group names.

Session IDs can be obtained in the logs or with the `sessions`_ RPC command.  Group
names can be obtained with the `groups`_ RPC command.

The special string :const:`all` disconnects all sessions.

Example::

  $ electrumx_rpc disconnect 209.59.102 34 2
  [
      "disconnecting session 34",
      "disconnecting group 209.59.102"
      "unknown: 2",
  ]

getinfo
-------

Return a summary of server state.  This command takes no arguments.
A typical result is as follows (with annotated comments)::

  $ electrumx_rpc getinfo
  {
      "coin": "Palladium",
      "daemon": "127.0.0.1:2332/",
      "daemon height": 542048,         # The daemon's height when last queried
      "db height": 542048,             # The height to which the DB is flushed
      "groups": 586,                   # The number of session groups
      "history cache": "185,014 lookups 9,756 hits 1,000 entries",
      "merkle cache": "280 lookups 54 hits 213 entries",
      "peers": {                       # Peer information
          "bad": 1,
          "good": 51,
          "never": 2,
          "stale": 0,
          "total": 54
      },
      "pid": 11804,                    # Process ID
      "request counts": {              # Count of RPC requests by method name
          "blockchain.block.header": 245,
          "blockchain.block.headers": 70,
          "blockchain.estimatefee": 12776,
          "blockchain.headers.subscribe": 2825,
          "blockchain.relayfee": 740,
          "blockchain.scripthash.get_history": 196,
          "blockchain.scripthash.subscribe": 184626,
          "blockchain.transaction.broadcast": 19,
          "blockchain.transaction.get": 213,
          "blockchain.transaction.get_merkle": 289,
          "getinfo": 3,
          "groups": 1,
          "mempool.get_fee_histogram": 3194,
          "mempool.get_info": 121,
          "server.add_peer": 9,
          "server.banner": 740,
          "server.donation_address": 754,
          "server.features": 50,
          "server.peers.subscribe": 792,
          "server.ping": 6412,
          "server.version": 2866
      },
      "request total": 216820,         # Total requests served
      "sessions": {                    # Live session stats
          "count": 670,
          "count with subs": 45,
          "errors": 0,
          "logged": 0,
          "paused": 0,
          "pending requests": 79,      # Number of requests currently being processed
          "subs": 36292                # Total subscriptions
      },
      "tx hashes cache": "289 lookups 38 hits 213 entries",
      "txs sent": 19,                  # Transactions broadcast
      "uptime": "01h 39m 04s",
      "version": "ElectrumX 1.10.1"
  }

Each ill-formed request, or one that does not follow the Electrum
protocol, increments the error count of the session that sent it.

:ref:`logging <session logging>` of sessions can be enabled by RPC.

For more information on peers see :ref:`here <peers>`.

Clients that are slow to consume data sent to them are :dfn:`paused` until their socket
buffer drains sufficiently, at which point processing of requests resumes.

Apart from very short intervals, typically after a new block or when a client has just
connected, the number of unprocessed requests should be low, say 250 or fewer.  If it is
over 1,000 the server is overloaded.

Sessions are put into groups, primarily as an anti-DoS measure. Each session goes into
a group based on its IP subnet (e.g. /24 for IPv4). Each member of a group incurs a fraction
of the costs of the other group members. This appears in the `sessions_` list under the
column XCost.

groups
------

Return a list of all current session groups.  Takes no arguments.

The output is quite similar to the `sessions`_ command.

log
---

Toggle logging of the given session IDs or group names.  All incoming requests for a
logged session are written to the server log.  The arguments are case-insensitive.

When a group is specified, logging is toggled for its current members only; there is no
effect on future group members.

Session IDs can be obtained in the logs or with the `sessions`_ RPC command.  Group
names can be obtained with the `groups`_ RPC command.

The special string :const:`all` turns on logging of all current and future sessions,
:const:`none` turns off logging of all current and future sessions, and :const:`new`
toggles logging of future sessions.

Example::

  $ electrumx_rpc log new 6 t0 z
  [
    "logging new sessions",
    "logging session 6",
    "logging session 3",
    "logging session 57",
    "logging session 12"
    "unknown: z",
  ]

In the above command sessions 3, 12 and 57 were in group `t0` (in fact, session 6 was
too).

.. _peers:

peers
-----

Return a list of peer Electrum servers serving the same coin network.
This command takes no arguments.

Peer data is obtained via a peer discovery protocol documented
:ref:`here <Peer Discovery>`::

  $ electrumx_rpc peers
  Host                           Status   TCP   SSL Server                  Min  Max  Pruning   Last Good    Last Try Tries               Source IP Address
  electrum1.example.com          good   50001 50002 plm-electrumx 1.0.0     1.4  1.7          07h 29m 23s 07h 30m 40s     0                 peer 192.0.2.10
  electrum2.example.com          good   50001 50002 plm-electrumx 1.0.0     1.4  1.7          07h 30m 34s 07h 30m 38s     0                 peer
  [...]

(The host names above are examples.)

.. _query:

query
-----

Run a query of the UTXO and history databases against one or more
addresses or hex scripts.  `--limit <N>` or `-l <N>` limits the output
for each kind to that many entries.  History is printed in blockchain
order; UTXOs in an arbitrary order.

For example::

  $ electrumx_rpc query --limit 5 76a91405d230d91166fa0e82b9142e66172846855e469a88ac
  Script: 76a91405d230d91166fa0e82b9142e66172846855e469a88ac
  History #0: height 28,227 txid 021bd9352ba2c0e8847f642753b0dea07db9fc76a991b154c8806b528280a1dc
  History #1: height 28,234 txid c7da889fdf7686a6f2f8a79ca1275b05b08f0d2f9051c85d1c2c70c0949ae025
  History #2: height 28,242 txid b940e1d63caf8b73562705df6bdf1f4c2e2ef47df5be46483c7ba4fd02fc7f66
  History #3: height 28,339 txid dd844c6838b9dfd18619dbf2816f22249c063755afaeaf67ed1e1118ad662616
  History #4: height 28,368 txid 0d95947d605984d6d1d32bc252af398a18e218fe4a7625c1496f88abd4a8a07e
  UTXO #1: txid 407a1be25f9962e83d1734fbf9773094428c77f835276cf965eef9f9778770c1 tx_pos 2 height 130,276 value 250,000,000
  UTXO #2: txid 0cd05022306e2cfdf30f1def563cb6fa2b5e0d13896da9531ce93c86296d8855 tx_pos 1 height 130,286 value 100,000,000
  UTXO #3: txid 6b172cf9477aec19198b89fa53600cfdb27ed0dd6d6c945ced5e0f02daa673fb tx_pos 1 height 130,359 value 300,000,000
  UTXO #4: txid b8a9992d63fa185c410f9d6855c39bc4afc0002b81b21a29c947aeac6f5b6428 tx_pos 0 height 130,447 value 250,000,000
  UTXO #5: txid 3cb0f3f21c8aad26293dd0228595c4f0f1c0e1f2863e756bb2d994e0fe2ba6a8 tx_pos 1 height 130,501 value 100,000,000
  Balance: 16.500000 PLM

reorg
-----

Force a block chain reorganisation, primarily for debugging purposes.
This command takes an optional argument - the number of blocks to
reorg - which defaults to 3.

That number of blocks will be backed up - using undo information
stored in ElectrumX's database - and then ElectrumX will move forwards
on the daemon's main chain to its current height.

.. _sessions:

sessions
--------

Return a list of all current sessions.  Takes no arguments::

  ID     Flags            Client Proto    Cost   XCost  Reqs   Txs    Subs    Recv Recv KB    Sent Sent KB      Time                  Peer
  1      S6                1.1.1   1.4       0      16     0     0       0       3       0       3       0    05m42s 165.255.191.213:22349
  2      S6       all_seeing_eye   1.4       0      16     0     0       0       2       0       2       0    05m40s   67.170.52.226:24995
  4      S6                3.3.2   1.4       0      16     0     0      34      45       5      45       3    05m40s 185.220.100.252:40463
  3      S6                1.1.2   1.4       0      16     0     0       0       3       0       3       0    05m40s    89.17.142.28:59241

The columns show information by session: the session ID, flags (see below), how the client
identifies itself - typically the Electrum client version, the protocol version
negotiated, the session cost, the additional session cost accrued from its groups, the
number of unprocessed requests, the number of transactions sent, the number of address
subscriptions, the number of requests received and their total size, the number of
messages sent and their size, how long the client has been connected, and the client's IP
address (if anonymous logging is disabled).

The flags are:

 * ``S`` an SSL connection
 * ``T`` a TCP connection
 * ``R`` a local RPC connection
 * ``L`` a logged session
 * ``C`` a connection that is being closed
 * the non-negative number is the connection "cost", with lower
   numbers having higher priority.  RPC connections have cost ``0``,
   normal connections have cost at least ``1``.

stop
----

Flush all cached data to disk and shut down the server cleanly, as if
sending the `KILL` signal.  Be patient - during initial sync flushing
all cached data to disk can take several minutes.  This command takes
no arguments.

.. _session logging:
