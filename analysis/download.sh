#! /bin/sh
set -e

HERE="$(readlink -f "$(dirname "$0")")"
. "${HERE}/secrets.sh"

# Works with "2026-02-27 10:00", "02/27/2026 10am", or even "today 10:00".

DATE="2026-02-27"
OUTPUT="right_open_to_car_1.csv"

cd "${HERE}/download"

poetry run python src/download/download.py \
       --manifest="${HERE}/training/manifest.yaml" \
       --output="${HERE}/training/${OUTPUT}" \
       --left-state "closed_car"
       --right-state "open" \
       --right-trans-to "closed_car" \
       --start "${DATE} 19:01:30" \
       --right-trans-time "${DATE} 19:01:57" \
       --end "${DATE} 19:20:00" \

# poetry run python src/download/download.py \
#        --manifest="${HERE}/training/manifest.json" \
#        --output="${HERE}/training/${OUTPUT}" \
#        --start "${DATE} 18:50:00" \
#        --end "${DATE} 19:00:00" \
#        --right-state "open" \
#        --right-trans-time "${DATE} 18:51:07" \
#        --right-trans-to "closed_empty" \
#        --left-state "closed_car"
