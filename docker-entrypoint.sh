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
