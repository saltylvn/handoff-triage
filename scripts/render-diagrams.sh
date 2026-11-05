#!/bin/sh
# Rebuilds docs/assets from the Mermaid sources in docs/diagrams.
# Usage: sh scripts/render-diagrams.sh [puppeteer-config.json]
set -eu
cd "$(dirname "$0")/.."
config=""
[ $# -ge 1 ] && config="-p $1"
for source in docs/diagrams/*.mmd; do
  name=$(basename "$source" .mmd)
  for format in svg png; do
    # shellcheck disable=SC2086
    npx -y @mermaid-js/mermaid-cli -q -i "$source" -o "docs/assets/$name.$format" \
      -c docs/diagrams/mermaid.config.json -b white -s 2 $config
  done
done
