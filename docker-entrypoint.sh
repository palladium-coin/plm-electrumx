#!/bin/sh
# Entrypoint of the plm-electrumx image: sets up SSL, then runs the server (the command given to the container).
#
# SSL_ENABLED   true (default) / false. If true, the server also listens on ssl://:50002.
# SSL_HOSTNAME  name (or IP) written in a generated certificate. Default: electrumx.
# SSL_CERTFILE, SSL_KEYFILE
#               paths of your own certificate and key (mounted in the container). If unset, the files
#               /var/lib/electrumx-ssl/server.crt and server.key are used; they are generated on the first
#               start (self-signed, 10 years) and reused on every later start, never overwritten.
# SERVICES      if unset: tcp://:50001, plus ssl://:50002 when SSL is enabled. If set, it is left as it is.
set -eu

SSL_DIR=/var/lib/electrumx-ssl
SSL_ENABLED="${SSL_ENABLED:-true}"
SSL_HOSTNAME="${SSL_HOSTNAME:-electrumx}"

log() { echo "entrypoint: $*"; }

for dir in "$DB_DIRECTORY" "$SSL_DIR"; do
    if [ ! -w "$dir" ]; then
        log "ERROR: $dir is not writable by uid $(id -u). Create the data directory on the host as that user, or set PLM_UID/PLM_GID (see README.md)." >&2
        exit 1
    fi
done

case "$SSL_ENABLED" in
    true|TRUE|True|1|yes|on)
        if [ -n "${SSL_CERTFILE:-}" ] || [ -n "${SSL_KEYFILE:-}" ]; then
            if [ -z "${SSL_CERTFILE:-}" ] || [ -z "${SSL_KEYFILE:-}" ]; then
                log "ERROR: set both SSL_CERTFILE and SSL_KEYFILE, or neither" >&2; exit 1
            fi
            if [ ! -r "$SSL_CERTFILE" ] || [ ! -r "$SSL_KEYFILE" ]; then
                log "ERROR: cannot read $SSL_CERTFILE / $SSL_KEYFILE (is it mounted, and readable by uid $(id -u)?)" >&2; exit 1
            fi
            log "using the SSL certificate $SSL_CERTFILE"
        else
            export SSL_CERTFILE="$SSL_DIR/server.crt"
            export SSL_KEYFILE="$SSL_DIR/server.key"
            if [ -e "$SSL_CERTFILE" ] && [ -e "$SSL_KEYFILE" ]; then
                log "using the existing SSL certificate $SSL_CERTFILE"
            elif [ -e "$SSL_CERTFILE" ] || [ -e "$SSL_KEYFILE" ]; then
                log "ERROR: only one of $SSL_CERTFILE and $SSL_KEYFILE exists; not overwriting it. Fix or remove it." >&2; exit 1
            else
                case "$SSL_HOSTNAME" in
                    *[!0-9.]*) san="DNS:$SSL_HOSTNAME" ;;
                    *)         san="IP:$SSL_HOSTNAME" ;;
                esac
                log "generating a self-signed SSL certificate for $SSL_HOSTNAME (valid 10 years) in $SSL_DIR"
                openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
                    -subj "/CN=$SSL_HOSTNAME" -addext "subjectAltName=$san" \
                    -keyout "$SSL_KEYFILE" -out "$SSL_CERTFILE" 2>/dev/null
                chmod 600 "$SSL_KEYFILE"
            fi
        fi
        log "certificate: $(openssl x509 -in "$SSL_CERTFILE" -noout -subject -enddate | tr '\n' ' ')"
        log "$(openssl x509 -in "$SSL_CERTFILE" -noout -fingerprint -sha256)"
        if ! openssl x509 -in "$SSL_CERTFILE" -noout -checkend 2592000 >/dev/null; then
            log "WARNING: the SSL certificate expires in less than 30 days or is already expired"
        fi
        export SERVICES="${SERVICES:-tcp://:50001,ssl://:50002}"
        ;;
    *)
        # empty values would be read by the server as "set"
        unset SSL_CERTFILE SSL_KEYFILE 2>/dev/null || true
        export SERVICES="${SERVICES:-tcp://:50001}"
        log "SSL disabled"
        ;;
esac

log "SERVICES=$SERVICES"
exec "$@"
