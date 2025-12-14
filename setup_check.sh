#!/bin/bash
# PhotoJobsTools Setup Check Script
# Checks for required dependencies and provides installation commands

set -e

echo "=========================================="
echo "PhotoJobsTools Setup Check"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

missing_deps=()
install_commands=()

# Check Python 3
echo "Checking Python 3..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python 3 found: $python_version"

    # Check if version is 3.9+
    python_major=$(echo $python_version | cut -d. -f1)
    python_minor=$(echo $python_version | cut -d. -f2)
    if [ "$python_major" -eq 3 ] && [ "$python_minor" -lt 9 ]; then
        echo -e "${YELLOW}⚠${NC} Warning: Python 3.9+ recommended (found $python_version)"
    fi
else
    echo -e "${RED}✗${NC} Python 3 not found"
    missing_deps+=("Python 3")
    install_commands+=("# Install Python 3 via Homebrew:")
    install_commands+=("brew install python3")
fi

# Check Pillow (PIL)
echo "Checking Pillow library..."
if /usr/bin/python3 -c "import PIL" &> /dev/null; then
    pillow_version=$(/usr/bin/python3 -c "import PIL; print(PIL.__version__)" 2>&1)
    echo -e "${GREEN}✓${NC} Pillow found (system Python): $pillow_version"
else
    echo -e "${YELLOW}⚠${NC} Pillow not found in system Python"
    missing_deps+=("Pillow (system Python)")
    install_commands+=("# Install Pillow for system Python:")
    install_commands+=("/usr/bin/python3 -m pip install --user Pillow")
fi

# Check exiftool
echo "Checking exiftool..."
if command -v exiftool &> /dev/null; then
    exiftool_version=$(exiftool -ver 2>&1)
    echo -e "${GREEN}✓${NC} exiftool found: $exiftool_version"
else
    echo -e "${RED}✗${NC} exiftool not found"
    missing_deps+=("exiftool")
    install_commands+=("# Install exiftool via Homebrew:")
    install_commands+=("brew install exiftool")
fi

# Check Homebrew (optional but recommended)
echo "Checking Homebrew..."
if command -v brew &> /dev/null; then
    brew_version=$(brew --version 2>&1 | head -n1)
    echo -e "${GREEN}✓${NC} Homebrew found: $brew_version"
else
    echo -e "${YELLOW}⚠${NC} Homebrew not found (optional, but recommended)"
    echo -e "    Homebrew makes installing dependencies easier"
    install_commands+=("# Install Homebrew (optional):")
    install_commands+=('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
fi

# Check git (should be available on macOS)
echo "Checking git..."
if command -v git &> /dev/null; then
    git_version=$(git --version 2>&1)
    echo -e "${GREEN}✓${NC} git found: $git_version"
else
    echo -e "${YELLOW}⚠${NC} git not found"
    echo -e "    Install Xcode Command Line Tools to get git"
    install_commands+=("# Install Xcode Command Line Tools (includes git):")
    install_commands+=("xcode-select --install")
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="

if [ ${#missing_deps[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All required dependencies are installed!${NC}"
    echo ""
    echo "You're ready to use PhotoJobsTools:"
    echo "  python3 -m photojobs --help"
else
    echo -e "${RED}Missing dependencies:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "=========================================="
    echo "Installation Commands"
    echo "=========================================="
    echo ""
    for cmd in "${install_commands[@]}"; do
        echo "$cmd"
    done
fi

echo ""
echo "=========================================="
echo "Optional: Install PhotoJobsTools Package"
echo "=========================================="
echo ""
echo "To install PhotoJobsTools as a package, run:"
echo "  cd $(dirname "$0")"
echo "  pip3 install --user -e ."
echo ""
echo "This will allow you to run 'photojobs' from anywhere."
echo ""

# Check if already installed
if python3 -c "import photojobs" &> /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PhotoJobsTools package is already installed"
else
    echo -e "${YELLOW}⚠${NC} PhotoJobsTools package not installed (optional)"
fi

echo ""
echo "Setup check complete!"
