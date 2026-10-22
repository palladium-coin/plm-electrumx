#!/bin/sh
# Checks the SSL handling of docker-entrypoint.sh in the image (no node needed).
# Usage: docker build -t plm-electrumx . && contrib/docker-smoke-test.sh [image]
set -eu
IMAGE="${1:-plm-electrumx}"
ENTRYPOINT=/usr/local/bin/docker-entrypoint.sh
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/db" "$tmp/ssl"

run() {  # extra docker args..., then the entrypoint is run with "echo ok"
    docker run --rm --user "$(id -u):$(id -g)" \
        -v "$tmp/db:/var/lib/electrumx" -v "$tmp/ssl:/var/lib/electrumx-ssl" \
        "$@" --entrypoint "$ENTRYPOINT" "$IMAGE" echo ok 2>&1
}
fingerprint() { openssl x509 -in "$tmp/ssl/server.crt" -noout -fingerprint -sha256; }
fail() { echo "FAIL: $*" >&2; exit 1; }

echo "1. first start generates a certificate and sets SERVICES"
out="$(run)"
echo "$out" | grep -q "generating a self-signed" || fail "no certificate generated: $out"
echo "$out" | grep -q "SERVICES=tcp://:50001,ssl://:50002" || fail "wrong SERVICES: $out"
[ -s "$tmp/ssl/server.key" ] || fail "no key"
first="$(fingerprint)"

echo "2. second start reuses it"
out="$(run)"
echo "$out" | grep -q "using the existing SSL certificate" || fail "not reused: $out"
[ "$(fingerprint)" = "$first" ] || fail "certificate changed"

echo "3. only one of the two files is an error, and nothing is overwritten"
rm "$tmp/ssl/server.key"
run | grep -q "ERROR: only one of" || fail "no error with a missing key"
[ ! -e "$tmp/ssl/server.key" ] || fail "key was recreated"

echo "4. SSL disabled"
run -e SSL_ENABLED=false | grep -q "SERVICES=tcp://:50001$" || fail "SSL not disabled"

echo "5. only SSL_CERTFILE is an error"
run -e SSL_CERTFILE=/nope.pem | grep -q "set both SSL_CERTFILE and SSL_KEYFILE" || fail "no error"

echo "6. a non-writable data directory is an error"
chmod 555 "$tmp/db"
if [ "$(id -u)" != 0 ]; then
    run | grep -q "is not writable" || fail "no error for a non-writable directory"
fi
chmod 755 "$tmp/db"

echo "OK"
