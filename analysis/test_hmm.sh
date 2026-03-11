#! /bin/sh
set -e
HERE="$(readlink -f "$(dirname "$0")")"
cd "${HERE}/training"
poetry run python src/training/test_hmm.py --model-dir . \
	--manifest "${HERE}/sonar_data/manifest.yaml" \
        "$@"
