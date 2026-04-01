#!/usr/bin/env bash
# Finarg installer — works on Linux, macOS, and WSL2.
# curl -fsSL https://raw.githubusercontent.com/Gantalf/finarg/main/scripts/install.sh | bash
set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { printf "${CYAN}▸${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}⚠${NC} %s\n" "$*"; }
fail()  { printf "${RED}✗${NC} %s\n" "$*"; exit 1; }

# ── Banner ──────────────────────────────────────────────────────────
printf "\n${BOLD}"
printf "  ╔══════════════════════════════════════╗\n"
printf "  ║                                      ║\n"
printf "  ║   ${GREEN}███████╗██╗███╗   ██╗${CYAN} █████╗ ${GREEN}██████╗${BOLD} ║\n"
printf "  ║   ${GREEN}██╔════╝██║████╗  ██║${CYAN}██╔══██╗${GREEN}██╔══██╗${BOLD}║\n"
printf "  ║   ${GREEN}█████╗  ██║██╔██╗ ██║${CYAN}███████║${GREEN}██████╔╝${BOLD}║\n"
printf "  ║   ${GREEN}██╔══╝  ██║██║╚██╗██║${CYAN}██╔══██║${GREEN}██╔══██╗${BOLD}║\n"
printf "  ║   ${GREEN}██║     ██║██║ ╚████║${CYAN}██║  ██║${GREEN}██║  ██║${BOLD}║\n"
printf "  ║   ${GREEN}╚═╝     ╚═╝╚═╝  ╚═══╝${CYAN}╚═╝  ╚═╝${GREEN}╚═╝  ╚═╝${BOLD}║\n"
printf "  ║                                      ║\n"
printf "  ║   ${NC}${BOLD}AI Financial Agent for LATAM${NC}${BOLD}        ║\n"
printf "  ╚══════════════════════════════════════╝${NC}\n\n"

# ── Detect OS ───────────────────────────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Linux*)  PLATFORM="linux" ;;
    Darwin*) PLATFORM="macos" ;;
    *)       fail "Unsupported OS: $OS. Use Linux, macOS, or WSL2." ;;
esac
info "Detected platform: $PLATFORM"

# ── Check Python ────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    warn "Python 3.11+ not found."
    if [ "$PLATFORM" = "macos" ]; then
        if command -v brew &>/dev/null; then
            info "Installing Python 3.11 via Homebrew..."
            brew install python@3.11
            PYTHON="python3.11"
        else
            fail "Install Python 3.11+: https://www.python.org/downloads/"
        fi
    else
        if command -v apt-get &>/dev/null; then
            info "Installing Python 3.11 via apt..."
            sudo apt-get update -qq && sudo apt-get install -y -qq python3.11 python3.11-venv python3-pip
            PYTHON="python3.11"
        elif command -v dnf &>/dev/null; then
            info "Installing Python 3.11 via dnf..."
            sudo dnf install -y python3.11
            PYTHON="python3.11"
        else
            fail "Install Python 3.11+: https://www.python.org/downloads/"
        fi
    fi
fi
ok "Python: $($PYTHON --version)"

# ── Check pip ───────────────────────────────────────────────────────
if ! $PYTHON -m pip --version &>/dev/null; then
    info "Installing pip..."
    $PYTHON -m ensurepip --upgrade 2>/dev/null || curl -sS https://bootstrap.pypa.io/get-pip.py | $PYTHON
fi
ok "pip available"

# ── Install pipx (for isolated install) ─────────────────────────────
if ! command -v pipx &>/dev/null; then
    info "Installing pipx..."
    $PYTHON -m pip install --user pipx 2>/dev/null
    $PYTHON -m pipx ensurepath 2>/dev/null
    export PATH="$HOME/.local/bin:$PATH"
fi

# ── Install Finarg ──────────────────────────────────────────────────
info "Installing Finarg..."
REPO_URL="git+https://github.com/Gantalf/finarg.git"
if command -v pipx &>/dev/null; then
    pipx install --force "$REPO_URL" 2>/dev/null
    ok "Installed via pipx (isolated environment)"
else
    $PYTHON -m pip install --user "$REPO_URL"
    ok "Installed via pip"
fi

# ── Install Node.js + agent-browser (for headless browser tools) ────
if command -v node &>/dev/null; then
    ok "Node.js: $(node --version)"
else
    info "Installing Node.js (needed for browser tools)..."
    if [ "$PLATFORM" = "macos" ] && command -v brew &>/dev/null; then
        brew install node
    elif command -v apt-get &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y nodejs
    else
        warn "Could not install Node.js automatically. Browser tools won't work."
        warn "Install manually: https://nodejs.org/"
    fi
fi

if command -v node &>/dev/null; then
    if command -v agent-browser &>/dev/null; then
        ok "agent-browser already installed"
    else
        info "Installing agent-browser (headless Chromium for browser tools)..."
        npm install -g agent-browser 2>/dev/null && agent-browser install 2>/dev/null
        if command -v agent-browser &>/dev/null; then
            ok "agent-browser installed"
        else
            warn "agent-browser install failed. Browser tools won't work, but everything else will."
            warn "Try manually: npm install -g agent-browser && agent-browser install"
        fi
    fi
fi

# ── Create config directory ─────────────────────────────────────────
FINARG_HOME="$HOME/.finarg"
mkdir -p "$FINARG_HOME/skills" "$FINARG_HOME/memories"
ok "Config directory: $FINARG_HOME"

# ── Verify ──────────────────────────────────────────────────────────
if command -v finarg &>/dev/null; then
    VERSION=$(finarg version 2>&1 || echo "installed")
    ok "$VERSION"
else
    # Might need shell reload
    export PATH="$HOME/.local/bin:$PATH"
    if command -v finarg &>/dev/null; then
        VERSION=$(finarg version 2>&1 || echo "installed")
        ok "$VERSION"
    else
        warn "finarg installed but not in PATH yet"
    fi
fi

# ── Done ────────────────────────────────────────────────────────────
printf "\n${BOLD}${GREEN}"
printf "  ╔══════════════════════════════════════╗\n"
printf "  ║  Installation complete!              ║\n"
printf "  ╚══════════════════════════════════════╝${NC}\n\n"

printf "  ${BOLD}Next steps:${NC}\n\n"
printf "    ${CYAN}source ~/.bashrc${NC}      # reload shell (or: source ~/.zshrc)\n"
printf "    ${CYAN}finarg init${NC}           # setup wizard (API keys)\n"
printf "    ${CYAN}finarg${NC}                # start chatting\n\n"
printf "  ${BOLD}Docs:${NC} https://github.com/Gantalf/finarg\n\n"
