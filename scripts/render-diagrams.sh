#!/bin/sh
# Rebuilds docs/assets from the two drawing scripts. PNGs are taken with headless Chrome.
set -eu
cd "$(dirname "$0")/.."
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
{ uv run python scripts/draw_diagrams.py; uv run python scripts/draw_system_map.py; } | while read -r name size; do
  scale=2
  [ "$name" = social-preview ] && scale=1 # GitHub wants this one at exactly 1280 by 640
  "$chrome" --headless --disable-gpu --force-device-scale-factor="$scale" --window-size="$size" \
    --hide-scrollbars --screenshot="$PWD/docs/assets/$name.png" \
    "file://$PWD/docs/assets/$name.svg" 2>/dev/null
done
