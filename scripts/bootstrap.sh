#!/usr/bin/env bash
# Reproduce the Arx build environment in a fresh (ephemeral) container: KiCad 9, the Python packages, make setup, then a self-test that prints versions.
# Idempotent and non-interactive. Installs only into the container (apt, /usr/local); it never removes a system package.
# usage: scripts/bootstrap.sh          (or as the SessionStart hook: .claude/hooks/session-start.sh)
set -euo pipefail
cd "$(dirname "$0")/.."
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
export DEBIAN_FRONTEND=noninteractive
say() { echo "[bootstrap] $*"; }

# 1. KiCad 9 from the official PPA. add-apt-repository is unreliable in this image, so the PPA is added by hand: the signing key comes from the Launchpad API + keyserver.
if command -v kicad-cli >/dev/null 2>&1 && kicad-cli version 2>/dev/null | grep -q '^9\.'; then
  say "KiCad $(kicad-cli version) already installed"
else
  say "installing KiCad 9 (PPA by hand)"
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq --no-install-recommends gnupg curl ca-certificates
  if [ ! -f /usr/share/keyrings/kicad9.gpg ]; then
    FP=$(curl -fsS "https://api.launchpad.net/devel/~kicad/+archive/ubuntu/kicad-9.0-releases" | python3 -c "import sys,json;print(json.load(sys.stdin)['signing_key_fingerprint'])")
    curl -fsS "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x${FP}" | gpg --dearmor | $SUDO tee /usr/share/keyrings/kicad9.gpg >/dev/null
  fi
  CODENAME=$(. /etc/os-release; echo "${VERSION_CODENAME}")
  echo "deb [signed-by=/usr/share/keyrings/kicad9.gpg] https://ppa.launchpadcontent.net/kicad/kicad-9.0-releases/ubuntu ${CODENAME} main" | $SUDO tee /etc/apt/sources.list.d/kicad9.list >/dev/null
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq --no-install-recommends kicad
fi

# 2. Python packages. Debian owns blinker; gerbonara -> quart -> flask wants blinker >= 1.9. --ignore-installed installs a second copy and removes nothing.
pipi() { pip install -q "$@" 2>/dev/null || pip install -q --break-system-packages "$@"; }
pipi --ignore-installed blinker
pipi -r requirements.txt

# 2b. Freerouting (src/pcb/freeroute.py): Java 25+ and the pinned jar. Optional: a failure here only disables the Freerouting step, so it warns and goes on.
if ! ls /usr/lib/jvm/java-2[5-9]-openjdk*/bin/java >/dev/null 2>&1; then
  $SUDO apt-get install -y -qq --no-install-recommends openjdk-25-jre-headless >/dev/null 2>&1 || say "WARNING: openjdk-25 not installed: Freerouting step unavailable"
fi
scripts/fetch_freerouting.sh >/dev/null 2>&1 || say "WARNING: Freerouting jar not fetched: Freerouting step unavailable"

# 3. repository work folder
make setup >/dev/null

# 4. self-test: every tool the sign-off needs must answer
fail=0
chk() { if "$@" >/dev/null 2>&1; then :; else echo "[bootstrap] SELF-TEST FAILED: $*"; fail=1; fi; }
chk python3 -c "import numpy, scipy, matplotlib, PIL, gerbonara, shapely"
chk kicad-cli version
chk /usr/bin/python3 -c "import pcbnew"
chk make --version
say "python      $(python3 --version 2>&1)"
say "numpy       $(python3 -c 'import numpy;print(numpy.__version__)') scipy $(python3 -c 'import scipy;print(scipy.__version__)') matplotlib $(python3 -c 'import matplotlib;print(matplotlib.__version__)')"
say "gerbonara   $(python3 -c 'import importlib.metadata as m;print(m.version("gerbonara"))' 2>/dev/null || echo ?) shapely $(python3 -c 'import shapely;print(shapely.__version__)')"
say "kicad-cli   $(kicad-cli version 2>&1 | head -1) | pcbnew $(/usr/bin/python3 -c 'import pcbnew;print(pcbnew.Version())' 2>&1 | tail -1)"
say "freerouting $(python3 -c 'import sys; sys.path.insert(0,"src/pcb"); import freeroute as F, os; print(F.VERSION, "jar ok" if os.path.exists(F.JAR) else "jar MISSING")' 2>/dev/null)"
say "work/       $(ls work | wc -l) files"
[ "$fail" -eq 0 ] && say "environment OK" || { say "environment INCOMPLETE"; exit 1; }
