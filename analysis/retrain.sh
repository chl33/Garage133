#! /bin/sh
set -e

here="$(readlink -f "$(dirname "$0")")"
cd "${here}/training"

poetry run python src/training/retrain.py \
    --manifest "${here}/sonar_data/manifest.yaml" \
    --model-dir . \
    "$@"
