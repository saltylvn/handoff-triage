#!/bin/sh
# Rebuilds the PNGs in docs/assets with headless Chrome (macOS).
# The pages are drawn as SVG into a temporary folder by scripts/visuals/, then photographed:
# 2400 by 1800 for the README pages, exactly 1280 by 640 for GitHub's social preview.
# The SVGs embed the system's SF Mono font when it's available, so only the PNGs are kept.
set -eu
cd "$(dirname "$0")/.."
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
{ (cd scripts/visuals && uv run python slides.py "$tmp" && uv run python canvas.py "$tmp"); } | while read -r name size; do
  scale=1.5
  [ "$name" = social-preview ] && scale=1
  "$chrome" --headless --disable-gpu --force-device-scale-factor="$scale" --window-size="$size" \
    --hide-scrollbars --screenshot="$PWD/docs/assets/$name.png" "file://$tmp/$name.svg" 2>/dev/null
done
# The eval chart is drawn from eval/results by the project's own code, and kept as SVG too.
uv run python -m triage.evals.chart
"$chrome" --headless --disable-gpu --force-device-scale-factor=2 --window-size=720,420 \
  --hide-scrollbars --screenshot="$PWD/docs/assets/threshold-tradeoff.png" \
  "file://$PWD/docs/assets/threshold-tradeoff.svg" 2>/dev/null
