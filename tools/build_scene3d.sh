#!/usr/bin/env bash
# Rebuilds site/vendor/scene3d.js (three.js + the 3D moment player) from site/src/scene3d.js.
# Needs node. Run from the repo root:  bash tools/build_scene3d.sh
set -euo pipefail
tmp="$(mktemp -d)"
cp site/src/scene3d.js "$tmp/scene3d.js"
(cd "$tmp" && npm init -y >/dev/null && npm install three@0.170.0 esbuild@0.24.0 --silent && \
  npx esbuild scene3d.js --bundle --minify --format=iife --global-name=KV3D --target=es2019 --outfile=scene3d.bundle.js)
cp "$tmp/scene3d.bundle.js" site/vendor/scene3d.js
ls -l site/vendor/scene3d.js
