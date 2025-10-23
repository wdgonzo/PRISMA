#!/bin/bash
################################################################################
# GSAS-II Compilation Script for Crux Supercomputer
# ==================================================
# Compiles GSAS-II from source for Python 3.11 + NumPy 2.2 compatibility
#
# Usage:
#   bash scripts/compile_gsas_crux.sh [gsas_source_dir]
#
# Arguments:
#   gsas_source_dir - Optional path to GSAS-II source (default: ../GSAS-II)
#
# This script:
# - Loads Crux compiler modules (GNU Fortran + C)
# - Installs Meson build system
# - Compiles GSAS-II Fortran/C extensions
# - Installs binaries to ~/.GSASII/bin/
# - Verifies compilation succeeded
#
# Author: William Gonzalez
# Date: January 2025
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================="
echo "GSAS-II Compilation for Crux"
echo "======================================================================="
echo ""

# Configuration
GSAS_SOURCE_DIR="${1:-${HOME}/GSAS-II}"
BUILD_DIR="${HOME}/.gsasii_build"
INSTALL_DIR="${HOME}/.GSASII/bin"

echo "Configuration:"
echo "  GSAS-II source: ${GSAS_SOURCE_DIR}"
echo "  Build directory: ${BUILD_DIR}"
echo "  Install directory: ${INSTALL_DIR}"
echo ""

# Step 1: Verify GSAS-II source exists
echo "Step 1: Verifying GSAS-II source directory..."
echo "-----------------------------------------------------------------------"

if [ ! -d "${GSAS_SOURCE_DIR}" ]; then
    echo -e "${RED}ERROR: GSAS-II source directory not found: ${GSAS_SOURCE_DIR}${NC}"
    echo ""
    echo "Please ensure GSAS-II is available at this location, or provide the path:"
    echo "  bash scripts/compile_gsas_crux.sh /path/to/GSAS-II"
    echo ""
    echo "To download GSAS-II:"
    echo "  git clone https://github.com/AdvancedPhotonSource/GSAS-II.git ${HOME}/GSAS-II"
    exit 1
fi

if [ ! -f "${GSAS_SOURCE_DIR}/sources/meson.build" ]; then
    echo -e "${RED}ERROR: ${GSAS_SOURCE_DIR} does not appear to be a valid GSAS-II source directory${NC}"
    echo "  Missing: sources/meson.build"
    exit 1
fi

echo -e "${GREEN}✓ GSAS-II source found${NC}"
echo ""

# Step 2: Load Crux modules
echo "Step 2: Loading Crux compiler modules..."
echo "-----------------------------------------------------------------------"

# Check if running on Crux
if [[ ! $(hostname) =~ crux ]]; then
    echo -e "${YELLOW}WARNING: Not running on Crux (hostname: $(hostname))${NC}"
    echo "Proceeding anyway, but module loading may fail..."
fi

# Load GNU programming environment (has gfortran)
echo "Loading PrgEnv-gnu..."
module load PrgEnv-gnu 2>/dev/null || {
    echo -e "${YELLOW}⚠ Could not load PrgEnv-gnu, trying to continue...${NC}"
}

# Load cray-python
echo "Loading cray-python/3.11.7..."
module load cray-python/3.11.7 2>/dev/null || {
    echo -e "${RED}ERROR: Could not load cray-python/3.11.7${NC}"
    echo "Available Python modules:"
    module avail python 2>&1 | grep -i python || echo "  None found"
    exit 1
}

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: ${PYTHON_VERSION}"

# Verify compilers are available
echo ""
echo "Verifying compilers..."
which ftn > /dev/null 2>&1 && echo "  ✓ Fortran compiler (ftn): $(which ftn)" || {
    echo -e "${RED}  ✗ Fortran compiler not found${NC}"
    exit 1
}
which cc > /dev/null 2>&1 && echo "  ✓ C compiler (cc): $(which cc)" || {
    echo -e "${RED}  ✗ C compiler not found${NC}"
    exit 1
}

# Check for gfortran (might be wrapped by ftn)
if command -v gfortran &> /dev/null; then
    echo "  ✓ gfortran: $(gfortran --version | head -1)"
fi

echo -e "${GREEN}✓ Compilers loaded${NC}"
echo ""

# Step 3: Install/verify Meson
echo "Step 3: Installing Meson build system..."
echo "-----------------------------------------------------------------------"

# Check if meson is already installed
if command -v meson &> /dev/null; then
    MESON_VERSION=$(meson --version)
    echo "Meson already installed: version ${MESON_VERSION}"
else
    echo "Installing meson via pip..."
    pip install --user meson ninja || {
        echo -e "${RED}ERROR: Failed to install meson${NC}"
        exit 1
    }

    # Add ~/.local/bin to PATH if not already there
    export PATH="${HOME}/.local/bin:${PATH}"

    if command -v meson &> /dev/null; then
        MESON_VERSION=$(meson --version)
        echo -e "${GREEN}✓ Meson installed: version ${MESON_VERSION}${NC}"
    else
        echo -e "${RED}ERROR: Meson installation failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Meson ready${NC}"
echo ""

# Step 4: Compile GSAS-II
echo "Step 4: Compiling GSAS-II..."
echo "-----------------------------------------------------------------------"

# Clean previous build if it exists
if [ -d "${BUILD_DIR}" ]; then
    echo "Removing previous build directory..."
    rm -rf "${BUILD_DIR}"
fi

# Set up build directory
echo "Setting up Meson build..."
cd "${GSAS_SOURCE_DIR}/sources"

# Configure with Meson
# Use environment variables to help Meson find Fortran compiler
export FC=ftn
export CC=cc

meson setup "${BUILD_DIR}" --prefix="${INSTALL_DIR}" || {
    echo -e "${RED}ERROR: Meson setup failed${NC}"
    echo ""
    echo "This usually means:"
    echo "  1. NumPy is not installed (required for f2py)"
    echo "  2. Fortran compiler not found"
    echo "  3. Incompatible Python/NumPy versions"
    echo ""
    echo "Debug information:"
    python3 -c "import numpy; print(f'NumPy: {numpy.__version__}')" 2>&1
    exit 1
}

echo ""
echo "Compiling (this may take 5-10 minutes)..."
meson compile -C "${BUILD_DIR}" || {
    echo -e "${RED}ERROR: Compilation failed${NC}"
    echo ""
    echo "Check the error messages above for details."
    echo "Common issues:"
    echo "  - Missing Fortran compiler flags"
    echo "  - Incompatible NumPy version"
    echo "  - Missing dependencies"
    exit 1
}

echo ""
echo "Installing binaries..."
meson install -C "${BUILD_DIR}" || {
    echo -e "${RED}ERROR: Installation failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ GSAS-II compiled successfully${NC}"
echo ""

# Step 5: Verify installation
echo "Step 5: Verifying GSAS-II binary installation..."
echo "-----------------------------------------------------------------------"

# Determine expected binary directory name
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
NPVER=$(python3 -c "import numpy; v=numpy.__version__.split('.'); print(f'{v[0]}.{v[1]}')")
BINARY_DIR="${INSTALL_DIR}/linux_64_p${PYVER}_n${NPVER}"

echo "Expected binary directory: ${BINARY_DIR}"

if [ -d "${BINARY_DIR}" ]; then
    echo -e "${GREEN}✓ Binary directory found${NC}"
elif [ -d "${INSTALL_DIR}" ]; then
    # List what was actually created
    echo -e "${YELLOW}⚠ Binary directory not at expected location${NC}"
    echo "Contents of ${INSTALL_DIR}:"
    ls -la "${INSTALL_DIR}"

    # Try to find binaries
    FOUND_DIR=$(find "${INSTALL_DIR}" -name "pyspg.*.so" -o -name "pyspg.*.pyd" | head -1 | xargs dirname 2>/dev/null || echo "")
    if [ -n "${FOUND_DIR}" ]; then
        echo ""
        echo -e "${GREEN}✓ Found binaries in: ${FOUND_DIR}${NC}"
        BINARY_DIR="${FOUND_DIR}"
    fi
else
    echo -e "${RED}✗ Installation directory not found${NC}"
    exit 1
fi

# Check for critical binaries
echo ""
echo "Checking for compiled binaries..."
BINARIES_OK=true

for binary in pyspg pypowder; do
    if ls "${BINARY_DIR}/${binary}".* 1> /dev/null 2>&1; then
        echo "  ✓ ${binary} found"
    else
        echo -e "  ${RED}✗ ${binary} NOT found${NC}"
        BINARIES_OK=false
    fi
done

if [ "$BINARIES_OK" = false ]; then
    echo ""
    echo -e "${RED}ERROR: Some binaries are missing${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All critical binaries present${NC}"
echo ""

# Step 6: Test import
echo "Step 6: Testing GSAS-II import..."
echo "-----------------------------------------------------------------------"

# Set GSAS-II environment
export GSAS2DIR="${GSAS_SOURCE_DIR}/GSASII"
export PYTHONPATH="${GSAS2DIR}:${PYTHONPATH}"

echo "Testing Python import..."
python3 << 'EOF'
import sys
import os

# Add GSAS-II to path
gsas_dir = os.environ.get('GSAS2DIR')
if gsas_dir and gsas_dir not in sys.path:
    sys.path.insert(0, gsas_dir)

try:
    # This will trigger binary loading
    import GSASIIpath
    GSASIIpath.SetBinaryPath(showConfigMsg=True)

    # Try to import a module that uses binaries
    from GSASII import pypowder

    print("\n✓ GSAS-II binaries loaded successfully!")
    print(f"  Binary path: {GSASIIpath.binaryPath}")

except Exception as e:
    print(f"\n✗ GSAS-II import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ GSAS-II import test passed${NC}"
else
    echo -e "${RED}✗ GSAS-II import test failed${NC}"
    exit 1
fi

echo ""
echo "======================================================================="
echo -e "${GREEN}GSAS-II Compilation Complete!${NC}"
echo "======================================================================="
echo ""
echo "Binary location: ${BINARY_DIR}"
echo "GSAS-II source:  ${GSAS2DIR}"
echo ""
echo "Environment variables (add to ~/.bashrc or activate script):"
echo "  export GSAS2DIR=${GSAS2DIR}"
echo "  export PYTHONPATH=\${GSAS2DIR}:\${PYTHONPATH}"
echo ""
echo "Next steps:"
echo "  1. Run headless GSAS-II initialization:"
echo "     python XRD/initialize_gsas_headless.py"
echo "  2. Test with your processing script:"
echo "     python XRD/data_visualization.py"
echo ""
echo "======================================================================="
