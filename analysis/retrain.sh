#! /bin/sh
set -e

train_args="--num-buckets 20"

here="$(readlink -f "$(dirname "$0")")"
cd "$here"
today=$(date +"%Y-%m-%d")
archive="training/Good/${today}"
mkdir "${archive}"
mv training/hmm*.json "${archive}"
./train-hmm.sh ${train_args}
./test_hmm.sh --all
