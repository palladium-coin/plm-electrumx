=============
plm-electrumx
=============

.. image:: https://github.com/palladium-coin/plm-electrumx/actions/workflows/ci.yml/badge.svg?branch=main
    :target: https://github.com/palladium-coin/plm-electrumx/actions/workflows/ci.yml

plm-electrumx is an Electrum protocol server for Palladium (PLM). It is a fork of
`spesmilo/electrumx <https://github.com/spesmilo/electrumx>`_ (which is itself a fork of
`kyuupichan/electrumx <https://github.com/kyuupichan/electrumx>`_) that supports Palladium only.

It connects to your Palladium full node and indexes the blockchain, allowing efficient
querying of history of arbitrary addresses. The server can be exposed publicly, and joined
to the network of servers via peer discovery.

The current version is |release|.

Source Code
===========

The project is hosted on `GitHub
<https://github.com/palladium-coin/plm-electrumx>`_ and uses `GitHub Actions
<https://github.com/palladium-coin/plm-electrumx/actions>`_ for Continuous
Integration.

Please submit an issue on the `bug tracker
<https://github.com/palladium-coin/plm-electrumx/issues>`_ if you have found a
bug or have a suggestion to improve the server.

Authors and License
===================

Neil Booth wrote the vast majority of the code; see :ref:`Authors`.
Python version at least 3.10 is required.

The code is released under the `MIT Licence
<https://github.com/palladium-coin/plm-electrumx/blob/main/LICENCE>`_.

Getting Started
===============

See :ref:`HOWTO`.

The repository also contains a :file:`Dockerfile` and a :file:`docker-compose.yml` that run the server next
to a Palladium node container; see `README.md <https://github.com/palladium-coin/plm-electrumx#with-docker-next-to-the-palladium-node>`_
and `DEPLOY.md <https://github.com/palladium-coin/plm-electrumx/blob/main/DEPLOY.md>`_ (ports, firewall, SSL, RPC credentials).

Documentation
=============

.. toctree::

   features
   changelog
   HOWTO
   environment
   protocol
   peer_discovery
   rpc-interface
   architecture
   authors

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
