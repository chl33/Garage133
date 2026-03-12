#! /bin/sh
set -e

HERE="$(readlink -f "$(dirname "$0")")"
. "${HERE}/secrets.sh"

cd "${HERE}/download/src"
poetry run python -m download.interactive "$@"
