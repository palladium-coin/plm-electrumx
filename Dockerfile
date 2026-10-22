# plm-electrumx: ElectrumX server for Palladium, with RocksDB, built from this source tree.
#
#   docker compose up -d --build        (see docker-compose.yml and README.md)
#
# Runs on the "palladium" network of the Palladium node container and reaches it as palladiumd:2332.

FROM python:3.14-trixie AS builder

WORKDIR /usr/src/app

# the libs needed by rocksdb (including development headers)
RUN apt-get update \
    && apt-get -y --no-install-recommends install \
        build-essential \
        librocksdb-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENCE MANIFEST.in ./
COPY src ./src
RUN python -m venv venv \
    && venv/bin/pip install --no-cache-dir ".[rocksdb]"


FROM python:3.14-slim-trixie

# the libs needed by rocksdb (no development headers or statics), and openssl to generate the SSL certificate
RUN apt-get update && apt-get -y --no-install-recommends install librocksdb9.10 openssl && rm -rf /var/lib/apt/lists/*

ENV COIN=Palladium
ENV NET=mainnet
ENV DB_ENGINE=rocksdb
ENV DB_DIRECTORY=/var/lib/electrumx
# SERVICES is set by docker-entrypoint.sh (tcp://:50001 and, with SSL, ssl://:50002), see there for the SSL settings.
# set at run time, see docker-compose.yml:
#ENV DAEMON_URL="http://user:password@palladiumd:2332/"
#ENV CACHE_MB=2000
#ENV REPORT_SERVICES=tcp://example.com:50001

WORKDIR /usr/src/app
COPY --from=builder /usr/src/app/venv ./venv
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# the data directories are created here so that empty volumes are owned by the electrumx user
RUN useradd --create-home --uid 1000 electrumx \
    && mkdir -p "$DB_DIRECTORY" /var/lib/electrumx-ssl \
    && chown electrumx:electrumx "$DB_DIRECTORY" /var/lib/electrumx-ssl
USER electrumx
VOLUME /var/lib/electrumx
VOLUME /var/lib/electrumx-ssl

# 50001: Electrum protocol over TCP, 50002: over SSL.
EXPOSE 50001 50002

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/src/app/venv/bin/electrumx_server"]
