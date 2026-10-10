#! /bin/sh
set -e
HERE="$(readlink -f "$(dirname "$0")")"
cd "${HERE}/training"

if [ "$#" -eq 0 ]; then
    poetry run python src/training/visualize_hmm.py hmm_left.json -o hmm_left.svg
    poetry run python src/training/visualize_hmm.py hmm_right.json -o hmm_right.svg
else
    poetry run python src/training/visualize_hmm.py "$@"
fi
