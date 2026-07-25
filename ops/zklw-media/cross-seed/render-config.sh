#!/usr/bin/env bash
# Render cross-seed's config on grey from secrets that already live there.
#
# Reads the qBittorrent password out of qbit-manage's config and the Prowlarr
# API key out of Prowlarr's config.xml, so this introduces no third copy of
# either secret. Neither value is ever echoed; the script reports lengths only.
#
# Usage (on grey):  bash render-config.sh [/path/to/config.template.js]
set -uo pipefail

TEMPLATE="${1:-/root/grey-ops/cross-seed-config.template.js}"
DEST_DIR="/home/mk/grey-media/config/cross-seed"
DEST="$DEST_DIR/config.js"
QBM="/home/mk/grey-media/config/qbit-manage/config.yml"
PROWLARR_XML="/home/mk/grey-media/config/prowlarr/config.xml"

[ -r "$TEMPLATE" ] || { echo "template not readable: $TEMPLATE" >&2; exit 1; }

# qbit password: the `pass:` key inside qbit-manage's `qbt:` block.
QBIT_PASS="$(awk '
  /^qbt:/            { inblk=1; next }
  inblk && /^[^ \t#]/ { inblk=0 }
  inblk && $1=="pass:" { sub(/^[ \t]*pass:[ \t]*/,""); gsub(/^["'"'"']|["'"'"']$/,""); print; exit }
' "$QBM" 2>/dev/null)"

PROWLARR_KEY="$(sed -n 's#.*<ApiKey>\([^<]*\)</ApiKey>.*#\1#p' "$PROWLARR_XML" 2>/dev/null | head -1)"

if [ -z "$QBIT_PASS" ] || [ -z "$PROWLARR_KEY" ]; then
  echo "FAILED to resolve secrets (qbit_pass=${#QBIT_PASS} chars, prowlarr_key=${#PROWLARR_KEY} chars)" >&2
  exit 2
fi
echo "resolved: qbit_pass=${#QBIT_PASS} chars, prowlarr_key=${#PROWLARR_KEY} chars"

mkdir -p "$DEST_DIR" "/data/cross-seeds/links"

# Substitute via a temp file with restrictive perms from the start, so the
# rendered secret is never briefly world-readable.
umask 077
TMP="$(mktemp)"
QBIT_PASS="$QBIT_PASS" PROWLARR_KEY="$PROWLARR_KEY" python3 - "$TEMPLATE" > "$TMP" <<'PY'
import os, sys, urllib.parse
src = open(sys.argv[1], encoding="utf-8").read()
# The password goes into a URL, so it must be percent-encoded or a '@' / ':'
# in the password silently truncates the host. This is exactly the class of bug
# that shows up as "cross-seed cannot reach qbit" with a correct-looking config.
src = src.replace("__QBIT_PASS__", urllib.parse.quote(os.environ["QBIT_PASS"], safe=""))
src = src.replace("__PROWLARR_KEY__", os.environ["PROWLARR_KEY"])
sys.stdout.write(src)
PY

if grep -q "__QBIT_PASS__\|__PROWLARR_KEY__" "$TMP"; then
  echo "substitution incomplete — refusing to install" >&2
  rm -f "$TMP"; exit 3
fi

mv "$TMP" "$DEST"
chmod 600 "$DEST"
echo "wrote $DEST ($(wc -c < "$DEST") bytes, mode 600)"
echo "posture: action=$(grep -o 'action: "[a-z]*"' "$DEST" | head -1), searchLimit=$(grep -o 'searchLimit: [0-9]*' "$DEST" | head -1)"
