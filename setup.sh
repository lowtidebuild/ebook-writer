#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────
# Ebook Writer Agent — Setup Script
# ─────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  📖 Ebook Writer Agent — Setup"
echo "  ─────────────────────────────"
echo ""

# ─────────────────────────────────────────────
# 1. OS Detection
# ─────────────────────────────────────────────
OS="$(uname -s)"
info "Detected OS: $OS"

# ─────────────────────────────────────────────
# 2. System Dependencies
# ─────────────────────────────────────────────
echo ""
info "Checking system dependencies..."

if [[ "$OS" == "Darwin" ]]; then
    if ! command -v brew &>/dev/null; then
        fail "Homebrew not found. Install from https://brew.sh"
        exit 1
    fi

    BREW_PKGS=(pango cairo gdk-pixbuf)
    for pkg in "${BREW_PKGS[@]}"; do
        if brew list "$pkg" &>/dev/null; then
            ok "$pkg already installed"
        else
            info "Installing $pkg..."
            brew install "$pkg"
            ok "$pkg installed"
        fi
    done

elif [[ "$OS" == "Linux" ]]; then
    LINUX_PKGS=(libpango1.0-dev libcairo2-dev libgdk-pixbuf2.0-dev)
    MISSING=()
    for pkg in "${LINUX_PKGS[@]}"; do
        if dpkg -s "$pkg" &>/dev/null 2>&1; then
            ok "$pkg already installed"
        else
            MISSING+=("$pkg")
        fi
    done
    if [[ ${#MISSING[@]} -gt 0 ]]; then
        info "Installing ${MISSING[*]}..."
        sudo apt-get update -qq && sudo apt-get install -y -qq "${MISSING[@]}"
        ok "System packages installed"
    fi
else
    warn "Unsupported OS ($OS). Install pango, cairo, gdk-pixbuf manually."
fi

# ─────────────────────────────────────────────
# 3. Fonts
# ─────────────────────────────────────────────
echo ""
info "Checking fonts..."

if [[ "$OS" == "Darwin" ]]; then
    FONT_CASKS=(font-noto-serif-cjk-kr font-noto-sans-cjk-kr font-fira-code)
    for cask in "${FONT_CASKS[@]}"; do
        if brew list --cask "$cask" &>/dev/null 2>&1; then
            ok "$cask already installed"
        else
            info "Installing $cask..."
            brew install --cask "$cask"
            ok "$cask installed"
        fi
    done

    # Pretendard — not available via brew, install manually
    PRETENDARD_DIR="$HOME/Library/Fonts"
    if ls "$PRETENDARD_DIR"/Pretendard-*.otf &>/dev/null 2>&1; then
        ok "Pretendard already installed"
    else
        info "Installing Pretendard font..."
        TMPDIR_FONT="$(mktemp -d)"
        curl -sL "https://github.com/orioncactus/pretendard/releases/latest/download/Pretendard-1.3.9.zip" \
            -o "$TMPDIR_FONT/pretendard.zip"
        unzip -qo "$TMPDIR_FONT/pretendard.zip" -d "$TMPDIR_FONT/pretendard"
        # Find and copy OTF files
        find "$TMPDIR_FONT/pretendard" -name "Pretendard-*.otf" -exec cp {} "$PRETENDARD_DIR/" \;
        rm -rf "$TMPDIR_FONT"
        ok "Pretendard installed to ~/Library/Fonts"
    fi

elif [[ "$OS" == "Linux" ]]; then
    FONT_PKGS=(fonts-noto-cjk fonts-firacode)
    MISSING=()
    for pkg in "${FONT_PKGS[@]}"; do
        if dpkg -s "$pkg" &>/dev/null 2>&1; then
            ok "$pkg already installed"
        else
            MISSING+=("$pkg")
        fi
    done
    if [[ ${#MISSING[@]} -gt 0 ]]; then
        info "Installing ${MISSING[*]}..."
        sudo apt-get install -y -qq "${MISSING[@]}"
        ok "Font packages installed"
    fi

    # Pretendard for Linux
    FONT_DIR="$HOME/.local/share/fonts"
    if ls "$FONT_DIR"/Pretendard-*.otf &>/dev/null 2>&1; then
        ok "Pretendard already installed"
    else
        info "Installing Pretendard font..."
        mkdir -p "$FONT_DIR"
        TMPDIR_FONT="$(mktemp -d)"
        curl -sL "https://github.com/orioncactus/pretendard/releases/latest/download/Pretendard-1.3.9.zip" \
            -o "$TMPDIR_FONT/pretendard.zip"
        unzip -qo "$TMPDIR_FONT/pretendard.zip" -d "$TMPDIR_FONT/pretendard"
        find "$TMPDIR_FONT/pretendard" -name "Pretendard-*.otf" -exec cp {} "$FONT_DIR/" \;
        rm -rf "$TMPDIR_FONT"
        fc-cache -f "$FONT_DIR"
        ok "Pretendard installed to ~/.local/share/fonts"
    fi
fi

# ─────────────────────────────────────────────
# 4. Python Virtual Environment
# ─────────────────────────────────────────────
echo ""
info "Setting up Python virtual environment..."

if ! command -v python3 &>/dev/null; then
    fail "python3 not found. Install Python 3.10+ first."
    exit 1
fi

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
info "Python version: $PY_VERSION"

if [[ -d ".venv" ]]; then
    ok ".venv already exists"
else
    info "Creating virtual environment..."
    python3 -m venv .venv
    ok ".venv created"
fi

info "Installing Python packages..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
ok "Python packages installed"

# ─────────────────────────────────────────────
# 5. Environment File
# ─────────────────────────────────────────────
echo ""
if [[ -f ".env" ]]; then
    ok ".env already exists"
else
    info "Creating .env template..."
    cat > .env <<'ENVEOF'
# Gemini API key for image generation (optional — pipeline works without it)
GEMINI_API_KEY=your-key-here
IMAGE_MODEL=gemini-2.0-flash-preview-image-generation
ENVEOF
    ok ".env template created — edit it to add your Gemini API key"
fi

# ─────────────────────────────────────────────
# 6. Verification
# ─────────────────────────────────────────────
echo ""
info "Verifying installation..."

ERRORS=0

# Check WeasyPrint import
if .venv/bin/python3 -c "import weasyprint" 2>/dev/null; then
    ok "weasyprint importable"
else
    fail "weasyprint import failed — check system dependencies (pango, cairo)"
    ERRORS=$((ERRORS + 1))
fi

# Check other packages
for pkg in markdown pymdownx pygments google.genai pymupdf; do
    mod_name="${pkg}"
    if .venv/bin/python3 -c "import ${mod_name}" 2>/dev/null; then
        ok "${mod_name} importable"
    else
        fail "${mod_name} import failed"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check output directory structure
EXPECTED_DIRS=(output/research output/outline output/chapters/ko output/chapters/en output/images output/edit output/final output/logs output/web-viewer)
for d in "${EXPECTED_DIRS[@]}"; do
    if [[ -d "$d" ]]; then
        ok "$d/ exists"
    else
        warn "$d/ missing — creating"
        mkdir -p "$d"
    fi
done

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "  ${GREEN}Setup complete!${NC}"
else
    echo -e "  ${YELLOW}Setup complete with $ERRORS warning(s).${NC}"
fi
echo ""
echo "  Next steps:"
echo "    1. Edit .env with your Gemini API key (optional)"
echo "    2. Open this project in Claude Code"
echo "    3. Run:  /generate \"Your Book Topic\""
echo ""
