#!/usr/bin/env bash
# Hakikisha kuna Node.js 20 au zaidi. Kama haipo kwenye server, pakua Node 22 (LTS)
# ndani ya folda .node/ ya mradi (start.sh inaiongeza kwenye PATH).
set -o errexit
node_inafaa() {
  command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'
}
export PATH="$PWD/.node/bin:$PATH"
if node_inafaa; then
  echo "Node $(node --version) ipo."
  exit 0
fi
echo "Node 20+ haipo; inapakua Node 22..."
BASE="https://nodejs.org/dist/latest-v22.x"
FAILI=$(curl -fsSL "$BASE/SHASUMS256.txt" | awk '/linux-x64\.tar\.xz$/ {print $2}')
HASH=$(curl -fsSL "$BASE/SHASUMS256.txt" | awk '/linux-x64\.tar\.xz$/ {print $1}')
curl -fsSL "$BASE/$FAILI" -o /tmp/node.tar.xz
echo "$HASH  /tmp/node.tar.xz" | sha256sum -c -
rm -rf .node && mkdir -p .node
tar -xJf /tmp/node.tar.xz -C .node --strip-components=1
rm -f /tmp/node.tar.xz
echo "Node $(.node/bin/node --version) imesakinishwa."
