# Palladium node in regtest mode, to run the integration tests of this repository against a real daemon.
# It runs the official release binaries (checked against the clearsigned SHA256SUMS.asc, which is checked against
# the pinned release key), with the palladium.conf next to this file.
#
#   docker compose -f tests/integration/docker-compose.yml up -d --build --wait
#
# Not for production: the RPC credentials are public and the chain is a throwaway regtest chain.

FROM ubuntu:22.04 AS fetch

ARG VERSION=2.1.0
# Fingerprint of palladium-release-key.asc, published in the release notes of the node
ARG RELEASE_FPR=70D5C2A2F6C5A128CD9223F227AB4AEDBF5D8BC1
# Set automatically by BuildKit: amd64, arm64 or arm
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /dl
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) T=x86_64-linux-gnu ;; \
      arm64) T=aarch64-linux-gnu ;; \
      arm)   T=arm-linux-gnueabihf ;; \
      *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    URL=https://github.com/palladium-coin/palladiumcore/releases/download/v${VERSION}; \
    F=palladium-${VERSION}-${T}.tar.gz; \
    for f in "$F" SHA256SUMS.asc palladium-release-key.asc; do curl -fsSLO "$URL/$f"; done; \
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --import palladium-release-key.asc; \
    gpg --with-colons --fingerprint | grep -q "^fpr:::::::::${RELEASE_FPR}:"; \
    gpg --status-fd 1 --output SHA256SUMS.signed --decrypt SHA256SUMS.asc | grep -q "^\[GNUPG:\] VALIDSIG ${RELEASE_FPR} "; \
    sha256sum -c --ignore-missing SHA256SUMS.signed; \
    tar xzf "$F" --strip-components=1 -C /usr/local palladium-${VERSION}/bin/palladiumd palladium-${VERSION}/bin/palladium-cli

FROM ubuntu:22.04

COPY --from=fetch /usr/local/bin/palladiumd /usr/local/bin/palladium-cli /usr/local/bin/

RUN useradd --create-home --uid 1000 palladium \
 && mkdir /home/palladium/.palladium && chown palladium:palladium /home/palladium/.palladium
COPY --chown=palladium:palladium palladium.conf /home/palladium/.palladium/palladium.conf
USER palladium

# regtest RPC and P2P
EXPOSE 28443 28444

# -daemon=0 and -regtest on the command line: they must not depend on the conf file
ENTRYPOINT ["palladiumd", "-printtoconsole", "-daemon=0", "-regtest"]
