.. _HOWTO:

=====
HOWTO
=====

Prerequisites
=============

**ElectrumX** should run on any flavour of unix.  I have run it
successfully on MacOS and DragonFlyBSD.  It won't run out-of-the-box
on Windows, but the changes required to make it do so should be
small - pull requests are welcome.

================ ========================
Package          Notes
================ ========================
Python3          ElectrumX uses asyncio.  Python version >= 3.10 is
                 **required**.
`aiohttp`_       Python library for asynchronous HTTP.  Version >=
                 2.0 required.
DB Engine        A database engine package is required; two are
                 supported (see `Database Engine`_ below).
================ ========================

You **must** be running a non-pruning Palladium daemon with::

  server=1
  txindex=1

set in its configuration file (:file:`palladium.conf`).  If you have an
existing installation of palladiumd and have not previously set
``txindex`` you will need to reindex the blockchain with::

  palladiumd -reindex

which can take some time.

While not a requirement for running ElectrumX, it is intended to be
run with supervisor software such as Daniel Bernstein's
`daemontools`_, Gerrit Pape's `runit`_ package or :command:`systemd`.
These make administration of secure unix servers very easy, and I
strongly recommend you install one of these and familiarise yourself
with them.  The instructions below and sample run scripts assume
``daemontools``; adapting to ``runit`` should be trivial for someone
used to either.

When building the database from the genesis block, ElectrumX has to
flush large quantities of data to disk and its DB.  You will have a
better experience if the database directory is on an SSD than on an
HDD.  At around height 542,000 of the Palladium blockchain the final
size of a RocksDB database, and other ElectrumX file metadata, is
roughly 230 MB.  The block chain only gets longer, so leave some room to
grow; a few GB of free space is plenty for now.

Database Engine
===============

You can choose from LevelDB and RocksDB to store transaction
information on disk.  On an SSD, RocksDB performs better than LevelDB.
We tried to support LMDB, but its history write performance
was much worse.

You will need to install one of:

+ `plyvel <https://plyvel.readthedocs.io/en/latest/installation.html>`_ for LevelDB.

  ``apt install libleveldb-dev build-essential``

  ``pip3 install plyvel`` , or use the ``[leveldb]`` extra install option to ElectrumX.

+ `rocksdb-ng <https://pypi.org/project/rocksdb-ng>`_ for RocksDB

  (Should work with RocksDB versions 8-10)

  ``apt install librocksdb-dev build-essential pkg-config``

  ``pip3 install rocksdb-ng`` , or use the ``[rocksdb]`` extra install option to ElectrumX.

+ `python-rocksdb <https://pypi.python.org/pypi/python-rocksdb>`_ for an unmaintained version
  that doesn't work with recent releases of RocksDB (only <7.0)

Running
=======

Install the prerequisites above.

Check out the code from Github::

    git clone https://github.com/palladium-coin/plm-electrumx.git
    cd plm-electrumx

You can install with::

    pip3 install .

There are many extra Python dependencies available to fit the needs of your
system or coins. For example, to install the RocksDB dependencies and a faster
JSON (de)serialization library::

    pip3 install ".[rocksdb,orjson]"

see pyproject.toml's ``project.optional-dependencies`` for a complete list.

You can also run the code from the source tree or a copy of it.


You should create a standard user account to run the server under;
your own is probably adequate unless paranoid.  The paranoid might
also want to create another user account for the daemontools logging
process.  The sample scripts and these instructions assume it is all
under one account which I have called ``electrumx``.

Next create a directory where the database will be stored and make it
writeable by the ``electrumx`` account.  I recommend this directory
live on an SSD::

    mkdir /path/to/db_directory
    chown electrumx /path/to/db_directory


Process limits
--------------

The ElectrumX process needs a large open file limit. On Linux systems,
the default (:command:`ulimit -n`) (soft) open file limit is usually 1,024.
ElectrumX tries to raise this automatically during startup to the hard limit,
which is usually 100,000+. If that fails (which would get logged),
you might have to manually increase the limit.

During sync it should not need more than about 1,024 open files.  When
serving it will use approximately 256 for LevelDB plus the number of
incoming connections.  It is not unusual to have 1,000 to 2,000
connections being served, so I suggest you set your open files limit
to at least 2,500.

Note that setting the limit in your shell does *NOT* affect ElectrumX
unless you are invoking ElectrumX directly from your shell.  If you
are using :command:`systemd`, you need to set it in the
:file:`.service` file (see `contrib/systemd/electrumx.service`_).


Using daemontools
-----------------

Next create a daemontools service directory; this only holds symlinks
(see daemontools documentation).  The :command:`svscan` program will
ensure the servers in the directory are running by launching a
:command:`supervise` supervisor for the server and another for its
logging process.  You can run :command:`svscan` under the *electrumx*
account if that is the only one involved (server and logger) otherwise
it will need to run as root so that the user can be switched to
electrumx.

Assuming this directory is called :file:`service`, you would do one
of::

    mkdir /service       # If running svscan as root
    mkdir ~/service      # As electrumx if running svscan as that a/c

Next create a directory to hold the scripts that the
:command:`supervise` process spawned by :command:`svscan` will run -
this directory must be readable by the :command:`svscan` process.
Suppose this directory is called :file:`scripts`, you might do::

    mkdir -p ~/scripts/electrumx

Then copy the all sample scripts from the ElectrumX source tree there::

    cp -R /path/to/repo/electrumx/contrib/daemontools ~/scripts/electrumx

This copies 3 things: the top level server run script, a :file:`log/`
directory with the logger :command:`run` script, an :file:`env/`
directory.

You need to configure the :ref:`environment variables <environment>`
under :file:`env/` to your setup.  ElectrumX server currently takes no
command line arguments; all of its configuration is taken from its
environment which is set up according to :file:`env/` directory (see
:manpage:`envdir` man page).  Finally you need to change the
:command:`log/run` script to use the directory where you want the logs
to be written by multilog.  The directory need not exist as
:command:`multilog` will create it, but its parent directory must
exist.

Now start the :command:`svscan` process.  This will not do much as the
service directory is still empty::

    svscan ~/service & disown

svscan is now waiting for services to be added to the directory::

    cd ~/service
    ln -s ~/scripts/electrumx electrumx

Creating the symlink will kick off the server process almost immediately.
You can see its logs with::

    tail -F /path/to/log/dir/current | tai64nlocal


Using systemd
-------------

This repository contains a sample systemd unit file that you can use
to setup ElectrumX with systemd. Simply copy it to
:file:`/etc/systemd/system`::

    cp contrib/systemd/electrumx.service /etc/systemd/system/

The sample unit file assumes that the repository is located at
:file:`/home/electrumx/electrumx`. If that differs on your system, you
need to change the unit file accordingly.

You need to set a few :ref:`environment variables <environment>` in
:file:`/etc/electrumx.conf`.

Now you can start ElectrumX using :command:`systemctl`::

    systemctl start electrumx

You can use :command:`journalctl` to check the log output::

    journalctl -u electrumx -f

Once configured you may want to start ElectrumX at boot::

    systemctl enable electrumx

.. Warning:: systemd is aggressive in forcibly shutting down
   processes.  Depending on your hardware, ElectrumX can need several
   minutes to flush cached data to disk during initial sync.  You
   should set TimeoutStopSec to *at least* 10 mins in your
   :file:`.service` file.


Sync Progress
=============

Time taken to index the blockchain depends on your hardware of course.
As Python is single-threaded most of the time only 1 core is kept
busy.  ElectrumX uses Python's :mod:`asyncio` to prefill a cache of
future blocks asynchronously to keep the CPU busy processing the chain
without pausing.

Consequently there will probably be only a minor boost in performance
if the daemon is on the same host.  It may even be beneficial to have
the daemon on a *separate* machine so the machine doing the indexing
has its caches and disk I/O tuned to that task only.

The :envvar:`CACHE_MB` environment variable controls the total cache
size ElectrumX uses; see :ref:`here <CACHE>` for caveats.

On a development machine (12 cores, RocksDB) with the daemon on the same host, building the database from
genesis to height 542,000 of the Palladium blockchain took about a minute.  Blocks are small and the chain is short,
so synchronization is much faster than for large chains; times on other hardware will vary.

.. note:: ElectrumX will not serve normal client connections until it
          has fully synchronized and caught up with your daemon.
          However LocalRPC connections are served at all times.


Terminating ElectrumX
=====================

The preferred way to terminate the server process is to send it the
``stop`` RPC command::

  electrumx_rpc stop

or alternatively on Unix the ``INT`` or ``TERM`` signals.  For a
daemontools supervised process this can be done by bringing it down
like so::

    svc -d ~/service/electrumx

ElectrumX will note receipt of the signals in the logs, and ensure the
block chain index is flushed to disk before terminating.  You should
be patient as flushing data to disk can take many minutes.

ElectrumX uses the transaction functionality, with fsync enabled, of
the databases.  I have written it with the intent that, to the extent
the atomicity guarantees are upheld by the DB software, the operating
system, and the hardware, the database should not get corrupted even
if the ElectrumX process if forcibly killed or there is loss of power.
The worst case should be having to restart indexing from the most
recent UTXO flush.

Once the process has terminated, you can start it up again with::

    svc -u ~/service/electrumx

You can see the status of a running service with::

    svstat ~/service/electrumx

:command:`svscan` can of course handle multiple services
simultaneously from the same service directory, such as a testnet
server.  See the man pages of these various commands for more
information.


Understanding the Logs
======================

You can see the logs usefully like so::

    tail -F /path/to/log/dir/current | tai64nlocal

Here is typical log output on startup::

  INFO:Controller:software version: plm-electrumx 1.0.0
  INFO:Controller:aiorpcX version: 0.25.0
  INFO:Controller:supported protocol versions: 1.4-1.7.0
  INFO:Controller:reorg limit is 200 blocks
  INFO:Daemon:daemon #1 at 127.0.0.1:2332/ (current)
  INFO:DB:switching current directory to /var/lib/electrumx
  INFO:DB:using rocksdb for DB backend
  INFO:DB:created new database
  INFO:DB:coin: Palladium
  INFO:DB:network: mainnet
  INFO:DB:height: -1
  INFO:DB:tx count: 0
  INFO:DB:flushing DB cache at 1,200 MB
  INFO:Prefetcher:catching up to daemon height 542,044 (542,045 blocks behind)
  INFO:Prefetcher:verified genesis block with hash 000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f
  INFO:BlockProcessor:our height: 9 daemon: 542,044 UTXOs 0MB hist 0MB
  [...]
  INFO:BlockProcessor:caught up to height 542047
  INFO:BlockProcessor:plm-electrumx 1.0.0 synced to height 542,047

While syncing, the ``our height`` lines repeat once or twice a minute with the
sizes of the caches, which are flushed to disk when they reach :envvar:`CACHE_MB`.
Once synced, the server follows new blocks and the mempool.

.. _SSL certificates:

Creating a self-signed SSL certificate
======================================

These instructions are based on those of the ``electrum-server``
documentation.

To run an SSL server you need to generate a self-signed certificate
using openssl.  Alternatively you could not set :envvar:`SSL_PORT` in
the environment and not serve over SSL, but this is not recommended.

Use the sample code below to create a self-signed cert with a
recommended validity of 5 years. You may supply any information for
your sign request to identify your server.  They are not currently
checked by the client except for the validity date.  When asked for a
challenge password just leave it empty and press enter::

    $ openssl genrsa -out server.key 2048
    $ openssl req -new -key server.key -out server.csr
    ...
    Country Name (2 letter code) [AU]:US
    State or Province Name (full name) [Some-State]:California
    Common Name (eg, YOUR name) []: electrum-server.tld
    ...
    A challenge password []:
    ...
    $ openssl x509 -req -days 1825 -in server.csr -signkey server.key -out server.crt

The :file:`server.crt` file goes in :envvar:`SSL_CERTFILE` and
:file:`server.key` in :envvar:`SSL_KEYFILE` in the server process's
environment.

Starting with Electrum 1.9, the client will learn and locally cache
the SSL certificate for your server upon the first request to prevent
man-in-the middle attacks for all further connections.

If your certificate is lost or expires on the server side, you will
need to run your server with a different server name and a new
certificate.  Therefore it's a good idea to make an offline backup
copy of your certificate and key in case you need to restore them.

Running on a privileged port
============================

You may choose to run electrumx on a different port than 50001
/ 50002.  If you choose a privileged port ( < 1024 ) it makes sense to
make use of a iptables NAT rule.

An example, which will forward Port 110 to the internal port 50002 follows::

    iptables -t nat -A PREROUTING -p tcp --dport 110 -j DNAT --to-destination 127.0.0.1:50002

You can then set the port as follows and advertise the service externally on the privileged port::

    REPORT_SSL_PORT=110


.. _`contrib/systemd/electrumx.service`: https://github.com/palladium-coin/plm-electrumx/blob/main/contrib/systemd/electrumx.service
.. _`daemontools`: http://cr.yp.to/daemontools.html
.. _`runit`: http://smarden.org/runit/index.html
.. _`aiohttp`: https://pypi.python.org/pypi/aiohttp
