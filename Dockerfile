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

# the libs needed by rocksdb (no development headers or statics)
RUN apt-get update && apt-get -y --no-install-recommends install librocksdb9.10 && rm -rf /var/lib/apt/lists/*

ENV COIN=Palladium
ENV NET=mainnet
ENV DB_ENGINE=rocksdb
ENV DB_DIRECTORY=/var/lib/electrumx
ENV SERVICES="tcp://:50001"
# set at run time, see docker-compose.yml:
#ENV DAEMON_URL="http://user:password@palladiumd:2332/"
#ENV CACHE_MB=2000
#ENV REPORT_SERVICES=tcp://example.com:50001

WORKDIR /usr/src/app
COPY --from=builder /usr/src/app/venv ./venv

# the data directory is created here so that an empty volume is owned by the electrumx user
RUN useradd --create-home --uid 1000 electrumx \
    && mkdir -p "$DB_DIRECTORY" && chown electrumx:electrumx "$DB_DIRECTORY"
USER electrumx
VOLUME /var/lib/electrumx

# 50001: Electrum protocol over TCP.
EXPOSE 50001

CMD ["/usr/src/app/venv/bin/electrumx_server"]
