#!/bin/sh
set -e

if [ -d "/work/src" ]; then
    export PYTHONPATH="/work/src:${PYTHONPATH}"
fi

case "$1" in
    ipsec-tui)
        shift
        exec ipsec-tui "$@"
        ;;
    ipsec-analyze)
        shift
        exec ipsec-analyze "$@"
        ;;
    pytest)
        shift
        exec pytest "$@"
        ;;
    sh|bash|/bin/sh|/bin/bash)
        exec "$@"
        ;;
    *)
        exec ipsec-analyze "$@"
        ;;
esac
