#!/bin/sh
set -e

if [ -d "/work/src" ]; then
    export PYTHONPATH="/work/src:${PYTHONPATH}"
fi

case "$1" in
    umbra-tui|ipsec-tui)
        shift
        exec umbra-tui "$@"
        ;;
    umbra|ipsec-analyze)
        shift
        exec umbra "$@"
        ;;
    umbra-web)
        shift
        # If the pre-built frontend exists (Dockerfile.web), point the
        # server at it so it works without a bind-mounted web-ui/dist.
        if [ -d "/opt/umbra-web/dist" ] && [ ! -d "/work/web-ui/dist" ]; then
            export UMBRA_STATIC_DIR="/opt/umbra-web/dist"
        fi
        exec python -m ipsec_analyzer.web "$@"
        ;;
    pytest)
        shift
        exec pytest "$@"
        ;;
    sh|bash|/bin/sh|/bin/bash)
        exec "$@"
        ;;
    *)
        exec umbra "$@"
        ;;
esac
