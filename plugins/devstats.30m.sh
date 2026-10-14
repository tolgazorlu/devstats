#!/bin/bash
# <swiftbar.title>Dev Stats</swiftbar.title>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisappear>true</swiftbar.hideDisappear>
# SwiftBar entry point: runs devstats.py from the repo's virtualenv.
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/devstats.py"
