#!/usr/bin/env bash
# CAD project (IC-CAD 2026) - local setup for macOS
# Usage:  bash setup_mac.sh /path/to/CAD      (defaults to the current folder)
#
# What it does:
#   1. Installs ngspice (Homebrew) and uv if they are missing
#   2. Creates CAD/.venv (Python 3.12) with all course packages
#   3. Patches ngspice_wrapper.py so it uses the server ngspice when it exists,
#      and the local ngspice otherwise (works on both, no need to revert)
#   4. Points VS Code at the .venv and installs the Python/Jupyter extensions
#   5. Verifies every package imports and that ngspice runs the TwoStage netlist
set -euo pipefail

CAD_DIR="$(cd "${1:-.}" && pwd)"
PACKAGES=(numpy scipy matplotlib pyyaml pandas gymnasium torch "mcp[cli]" pydantic python-dotenv ipykernel pytest)

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32m✓\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m✗ %s\033[0m\n' "$*"; exit 1; }

[ -d "$CAD_DIR/ngspice_interface" ] || fail "$CAD_DIR doesn't look like the CAD folder (no ngspice_interface/). Run: bash setup_mac.sh /path/to/CAD"
echo "CAD folder: $CAD_DIR"

# ---------------------------------------------------------------- Homebrew
find_brew() {
  for b in "$(command -v brew 2>/dev/null || true)" "$HOME/.homebrew/bin/brew" /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -n "$b" ] && [ -x "$b" ] && { echo "$b"; return; }
  done
}

# ---------------------------------------------------------------- 1. ngspice
say "ngspice"
if command -v ngspice >/dev/null 2>&1; then
  ok "already installed: $(command -v ngspice)"
else
  BREW="$(find_brew)"
  [ -n "$BREW" ] || fail "Homebrew not found. Install it from https://brew.sh, then re-run this script."
  eval "$("$BREW" shellenv)"
  "$BREW" install ngspice
  ok "installed: $(command -v ngspice)"
fi
NGSPICE="$(command -v ngspice)"

# ---------------------------------------------------------------- uv
say "uv"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
ok "$(uv --version)"

# ---------------------------------------------------------------- 2. venv + packages
say "Python environment (CAD/.venv, Python 3.12)"
cd "$CAD_DIR"
[ -x .venv/bin/python ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python "${PACKAGES[@]}"
.venv/bin/python -m ipykernel install --user --name cad_env --display-name "Python (cad_env)" >/dev/null
ok "packages installed, Jupyter kernel 'cad_env' registered"

# ---------------------------------------------------------------- 3. patch ngspice path
say "ngspice path in ngspice_wrapper.py"
.venv/bin/python - "$CAD_DIR/ngspice_interface/ngspice_wrapper.py" <<'PY'
import sys, shutil
p = sys.argv[1]
src = open(p).read()
if "NGSPICE_BIN" in src:
    print("    already patched"); sys.exit(0)
old = '"/users/micas/mahmadza/public/bin/ngspice -b %s >/dev/null 2>&1" %netlist_path'
if old not in src:
    print("    !! simulate() line not found - edit it by hand to use 'ngspice'"); sys.exit(0)
shutil.copy(p, p + ".bak")
header = (
    "import shutil\n"
    "# Server ngspice if it exists (ESAT), otherwise the one on PATH (your own computer)\n"
    "_SERVER_NGSPICE = \"/users/micas/mahmadza/public/bin/ngspice\"\n"
    "NGSPICE_BIN = _SERVER_NGSPICE if os.path.exists(_SERVER_NGSPICE) else (shutil.which(\"ngspice\") or \"ngspice\")\n"
)
src = src.replace("import time \n", "import time \n" + header, 1) if "import time \n" in src \
      else src.replace("import os\n", "import os\n" + header, 1)
src = src.replace(old, 'NGSPICE_BIN + " -b %s >/dev/null 2>&1" % netlist_path')
open(p, "w").write(src)
print("    patched (backup: ngspice_wrapper.py.bak)")
PY

# ---------------------------------------------------------------- 4. VS Code
say "VS Code"
CODE_APP="/Applications/Visual Studio Code.app"
if [ "$(uname)" = "Darwin" ] && [ ! -d "$CODE_APP" ] && [ ! -d "$HOME/Applications/Visual Studio Code.app" ]; then
  BREW="$(find_brew)"
  if [ -n "$BREW" ]; then "$BREW" install --cask visual-studio-code; else echo "    Install VS Code from https://code.visualstudio.com"; fi
fi
CODE_CLI="$(command -v code 2>/dev/null || true)"
for c in "$CODE_APP/Contents/Resources/app/bin/code" "$HOME/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"; do
  [ -z "$CODE_CLI" ] && [ -x "$c" ] && CODE_CLI="$c"
done
if [ -n "$CODE_CLI" ]; then
  "$CODE_CLI" --install-extension ms-python.python --force >/dev/null 2>&1 || true
  "$CODE_CLI" --install-extension ms-toolsai.jupyter --force >/dev/null 2>&1 || true
  ok "Python + Jupyter extensions installed"
fi
mkdir -p .vscode
if [ ! -f .vscode/settings.json ]; then
  cat > .vscode/settings.json <<'JSON'
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true
}
JSON
  ok "wrote .vscode/settings.json (interpreter = .venv)"
else
  ok ".vscode/settings.json exists - select .venv via 'Python: Select Interpreter' if needed"
fi

# ---------------------------------------------------------------- 5. verify
say "Verifying"
.venv/bin/python - <<'PY'
import importlib, sys
mods = {"numpy":"numpy","scipy":"scipy","matplotlib":"matplotlib","pyyaml":"yaml","pandas":"pandas",
        "gymnasium":"gymnasium","torch":"torch","mcp":"mcp","pydantic":"pydantic",
        "python-dotenv":"dotenv","ipykernel":"ipykernel"}
bad = []
for name, mod in mods.items():
    try:
        m = importlib.import_module(mod)
        print(f"    \033[32m✓\033[0m {name:14s} {getattr(m, '__version__', '')}")
    except Exception as e:
        bad.append(name); print(f"    \033[31m✗\033[0m {name:14s} {e}")
import torch
print(f"      torch MPS (Apple GPU) available: {torch.backends.mps.is_available()}")
print(f"    Python {sys.version.split()[0]}")
sys.exit(1 if bad else 0)
PY

NETLIST="ngspice_interface/files/input_netlists/TwoStage.cir"
if [ -f "$NETLIST" ]; then
  if "$NGSPICE" -b "$NETLIST" >/tmp/cad_ngspice_test.log 2>&1; then
    ok "ngspice ran $NETLIST ($("$NGSPICE" -v 2>/dev/null | grep -m1 -o 'ngspice-[0-9]*' || echo ngspice))"
  else
    tail -20 /tmp/cad_ngspice_test.log; fail "ngspice failed on $NETLIST (log: /tmp/cad_ngspice_test.log)"
  fi
fi

say "Done. Open the CAD folder in VS Code:  code \"$CAD_DIR\""
