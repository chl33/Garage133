#! /bin/sh
set -e

# ./download.sh -s 31 -d 30 --left-state closed_car --right-state closed_car
# ./download.sh --start 21:00 --end 21:10 --left-state closed_car --right-state closed_car

HERE="$(readlink -f "$(dirname "$0")")"
. "${HERE}/secrets.sh"

cd "${HERE}/download/src/"
poetry run python -m download.download "$@"
