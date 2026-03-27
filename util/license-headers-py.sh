#! /bin/sh
set -e
cd "$(dirname "$0")"/..
license-header-checker -r -i .git,.github,.pio,.ccls-cache \
	-a ./util/license_header_py.txt . py
