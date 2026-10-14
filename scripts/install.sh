#!/bin/bash
# Install Dev Stats: Python env, SwiftBar menu bar plugin and (optionally) the desktop widget.
# Idempotent. Never touches API keys: run scripts/configure.py for those.
# Usage: scripts/install.sh [--no-widget]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$HOME/.config/asc-menubar"
WIDGET=1
[[ "${1:-}" == "--no-widget" ]] && WIDGET=0

step() { printf '\n==> %s\n' "$1"; }
need_brew() {
  command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
}

step "Python environment"
# The Python that ships with the Xcode command line tools (3.9) no longer gets security
# fixes, so prefer a supported interpreter and rebuild an old venv.
pick_python() {
  # Homebrew first: a stable, user-managed interpreter the venv can keep pointing at.
  for p in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.13 \
           /usr/local/bin/python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 \
           python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
      command -v "$p"; return 0
    fi
  done
  return 1
}
PY="$(pick_python)" || { echo "Python 3.10+ is required (brew install python)"; exit 1; }
if [[ -x "$ROOT/.venv/bin/python" ]] && ! "$ROOT/.venv/bin/python" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "rebuilding .venv on $("$PY" --version)"
  rm -rf "$ROOT/.venv"
fi
[[ -x "$ROOT/.venv/bin/python" ]] || "$PY" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -q --disable-pip-version-check -r "$ROOT/requirements.txt"

step "SwiftBar"
if [[ ! -d /Applications/SwiftBar.app ]]; then
  need_brew
  brew install --cask swiftbar
fi
chmod +x "$ROOT/plugins/devstats.30m.sh"
CURRENT_DIR="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
if [[ -z "$CURRENT_DIR" ]]; then
  defaults write com.ameba.SwiftBar PluginDirectory "$ROOT/plugins"
  echo "SwiftBar plugin folder set to $ROOT/plugins"
elif [[ "$CURRENT_DIR" != "$ROOT/plugins" ]]; then
  # keep the user's existing plugin folder, link ours into it
  ln -sf "$ROOT/plugins/devstats.30m.sh" "$CURRENT_DIR/devstats.30m.sh"
  echo "Linked plugin into existing SwiftBar folder $CURRENT_DIR"
fi

step "Credentials"
if [[ -f "$CONFIG_DIR/config.json" ]]; then
  echo "found $CONFIG_DIR/config.json"
else
  echo "No App Store Connect config yet. Run:"
  echo "  $ROOT/.venv/bin/python $ROOT/scripts/configure.py --issuer-id ... --key-id ... --vendor-number ... --p8 ~/Downloads/AuthKey_XXXX.p8"
fi
command -v gh >/dev/null && gh auth status >/dev/null 2>&1 \
  && echo "GitHub CLI is logged in" \
  || echo "GitHub stats need the GitHub CLI: brew install gh && gh auth login"

if [[ $WIDGET == 1 ]]; then
  step "Desktop widget"
  if ! xcodebuild -version >/dev/null 2>&1; then
    echo "Xcode not found, skipping the widget (menu bar still works)."
  else
    command -v xcodegen >/dev/null || { need_brew; brew install xcodegen; }
    cd "$ROOT/widget"
    if [[ ! -f Local.xcconfig ]]; then
      TEAM="$(security find-certificate -c "Apple Development" -p 2>/dev/null \
        | openssl x509 -noout -subject 2>/dev/null | sed -n 's/.*OU *= *\([A-Z0-9]*\).*/\1/p')"
      if [[ -z "$TEAM" ]]; then
        echo "No Apple Development certificate found. Sign in to Xcode (Settings > Accounts),"
        echo "or copy Local.xcconfig.example to Local.xcconfig and set DEVELOPMENT_TEAM."
        exit 1
      fi
      printf 'DEVELOPMENT_TEAM = %s\nDEVSTATS_BUNDLE_PREFIX = com.%s.local\n' "$TEAM" "$(whoami | tr -cd 'a-z0-9')" > Local.xcconfig
      echo "wrote widget/Local.xcconfig (team $TEAM)"
    fi
    xcodegen generate --quiet
    xcodebuild -project DevStats.xcodeproj -scheme DevStats -configuration Release \
      -destination 'generic/platform=macOS' \
      -derivedDataPath build -allowProvisioningUpdates -quiet build
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/DevStats.app"
    cp -R build/Build/Products/Release/DevStats.app "$HOME/Applications/"
    open "$HOME/Applications/DevStats.app"
    echo "Installed ~/Applications/DevStats.app. Add the widget: right-click the desktop > Edit Widgets > Dev Stats."
  fi
fi

step "First run"
open -a SwiftBar 2>/dev/null || open /Applications/SwiftBar.app
sleep 2
open -g "swiftbar://refreshallplugins" || true
echo "Done. Menu bar item: App Store downloads this week + GitHub contributions today."
