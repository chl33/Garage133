#! /bin/sh
set -e
HERE="$(readlink -f "$(dirname "$0")")"
cd "${HERE}/training"
poetry run python src/training/train_hmm.py \
	--manifest "${HERE}/sonar_data/manifest.yaml" \
	"$@"
