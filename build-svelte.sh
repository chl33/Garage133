#! /bin/sh
set -e
here="$(readlink -f "$(dirname "$0")")"
cd "$here/svelte"
npm run build
npx svelteesp32 -e psychic -s dist -o ../src/svelteesp32async.h --etag=true
