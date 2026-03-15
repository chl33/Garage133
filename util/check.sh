#! /bin/sh
set -e
root="$(readlink -f "$(dirname "$0")"/..)"
cd "$root"
./util/license-headers.sh
./util/license-headers-py.sh
pio test -e native
