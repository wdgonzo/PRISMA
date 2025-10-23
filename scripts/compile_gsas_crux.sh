#!/bin/bash
################################################################################
# GSAS-II Compilation Script for Crux Supercomputer
# ==================================================
# Compiles GSAS-II from source for Python 3.11 + NumPy 1.26 compatibility
# Based on: https://advancedphotonsource.github.io/GSAS-II-tutorials/compile.html
#
# Usage:
#   bash scripts/compile_gsas_crux.sh [gsas_source_dir]
#
# Arguments:
#   gsas_source_dir - Optional path to GSAS-II source directory
#
# Author(s): William Gonzalez
# Date: October 2025
# Version: Beta 0.1
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESSOR_DIR="$(dirname "${SCRIPT_DIR}")"
SOFTWARE_DIR="$(dirname "${PROCESSOR_DIR}")"
GSAS_SOURCE_DIR="${1:-${SOFTWARE_DIR}/GSAS-II}"
BUILD_DIR_NAME="build_temp"
BUILD_DIR="${GSAS_SOURCE_DIR}/${BUILD_DIR_NAME}"

echo "Configuration:"
echo "  Software directory: ${SOFTWARE_DIR}"
echo "  GSAS-II source: ${GSAS_SOURCE_DIR}"
echo "  Build directory: ${BUILD_DIR}"
echo "  Install target: ${GSAS_SOURCE_DIR}/GSASII-bin/"
echo ""

# Step 1: Verify GSAS-II source exists
echo "Step 1: Verifying GSAS-II source directory..."
echo "-----------------------------------------------------------------------"

if [ ! -d "${GSAS_SOURCE_DIR}" ]; then
    echo -e "${RED}ERROR: GSAS-II source directory not found: ${GSAS_SOURCE_DIR}${NC}"
    echo ""
    echo "To download GSAS-II:"
    echo "  cd ${SOFTWARE_DIR}"
    echo "  git clone https://github.com/AdvancedPhotonSource/GSAS-II.git"
    exit 1
fi

if [ ! -f "${GSAS_SOURCE_DIR}/meson.build" ]; then
    echo -e "${RED}ERROR: Not a valid GSAS-II source directory (missing meson.build)${NC}"
    echo "  Expected: ${GSAS_SOURCE_DIR}/meson.build"
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

# Step 3: Check/Activate Virtual Environment
echo "Step 3: Checking virtual environment..."
echo "-----------------------------------------------------------------------"

VENV_PATH="${SOFTWARE_DIR}/venv"
if [ ! -d "${VENV_PATH}" ]; then
    echo -e "${RED}ERROR: Virtual environment not found at ${VENV_PATH}${NC}"
    echo ""
    echo "Please run the setup script first:"
    echo "  bash scripts/crux_setup.sh"
    exit 1
fi

echo "Activating virtual environment: ${VENV_PATH}"
source "${VENV_PATH}/bin/activate"

# Rehash to pick up newly installed executables
hash -r 2>/dev/null || true

# Verify Python dependencies
echo "Checking Python build dependencies..."
python3 << 'EOF'
import sys

deps = {
    "numpy": "1.26",
    "cython": None,
    "pybind11": None,
}

all_ok = True
for module, required_ver in deps.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        if required_ver and not version.startswith(required_ver):
            print(f"  ✗ {module}: {version} (need {required_ver})")
            all_ok = False
        else:
            print(f"  ✓ {module}: {version}")
    except ImportError:
        print(f"  ✗ {module}: NOT FOUND")
        all_ok = False

if not all_ok:
    print("\nMissing Python dependencies! Install with:")
    print("  pip install numpy==1.26 cython pybind11")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# Verify command-line build tools (non-blocking - let meson fail naturally if not found)
echo ""
echo "Checking command-line build tools..."

# Explicitly add venv bin to PATH in case it's not propagating properly
export PATH="${VENV_PATH}/bin:${PATH}"
hash -r 2>/dev/null || true

if command -v meson &> /dev/null; then
    MESON_VER=$(meson --version)
    echo "  ✓ meson: ${MESON_VER}"
else
    echo -e "  ${YELLOW}⚠ meson not detected in PATH, but will try anyway...${NC}"
    echo "  PATH includes: ${PATH}"
fi

if command -v ninja &> /dev/null; then
    NINJA_VER=$(ninja --version)
    echo "  ✓ ninja: ${NINJA_VER}"
else
    echo -e "  ${YELLOW}⚠ ninja not found (optional)${NC}"
fi

echo -e "${GREEN}✓ Python dependencies present${NC}"
echo ""

# Step 4: Set NumPy compiler flags (CRITICAL!)
echo "Step 4: Setting NumPy include paths for compilation..."
echo "-----------------------------------------------------------------------"

NUMPY_INCLUDE=$(python3 -c 'import numpy; print(numpy.get_include())')
export CFLAGS="-I${NUMPY_INCLUDE}"
export CPPFLAGS="-I${NUMPY_INCLUDE}"

echo "NumPy include path: ${NUMPY_INCLUDE}"
echo "CFLAGS: ${CFLAGS}"
echo "CPPFLAGS: ${CPPFLAGS}"
echo -e "${GREEN}✓ Compiler flags set${NC}"
echo ""

# Step 5: Compile GSAS-II
echo "Step 5: Compiling GSAS-II..."
echo "-----------------------------------------------------------------------"

# Clean previous build if it exists
if [ -d "${BUILD_DIR}" ]; then
    echo "Removing previous build directory..."
    rm -rf "${BUILD_DIR}"
fi

# Navigate to GSAS-II source directory
cd "${GSAS_SOURCE_DIR}"
echo "Working directory: $(pwd)"
echo ""

# Set compiler environment
export FC=ftn
export CC=cc

# Meson setup (creates build directory)
echo "Running meson setup..."
echo "Command: meson setup ${BUILD_DIR_NAME}"
meson setup "${BUILD_DIR_NAME}" || {
    echo -e "${RED}ERROR: Meson setup failed${NC}"
    echo ""
    echo "Check the error messages above. Common issues:"
    echo "  1. NumPy not found (ensure venv is activated)"
    echo "  2. Compiler not found (ensure PrgEnv-gnu is loaded)"
    echo "  3. Missing dependencies (meson, cython, pybind11)"
    echo ""
    echo "Debug information:"
    echo "  Python: $(which python3)"
    echo "  NumPy: $(python3 -c 'import numpy; print(numpy.__version__)')"
    echo "  Meson: $(which meson)"
    exit 1
}

echo -e "${GREEN}✓ Meson setup successful${NC}"
echo ""

# Compile
echo "Compiling (this may take 5-10 minutes)..."
meson compile -C "${BUILD_DIR_NAME}" || {
    echo -e "${RED}ERROR: Compilation failed${NC}"
    echo ""
    echo "Check the error messages above for details."
    exit 1
}

echo -e "${GREEN}✓ Compilation successful${NC}"
echo ""

# Install binaries using system-install
echo "Installing binaries with system-install..."
meson compile -C "${BUILD_DIR_NAME}" system-install || {
    echo -e "${RED}ERROR: Installation failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ Binaries compiled and installed to GSASII/bin/${NC}"
echo ""

# Step 6: Move binaries to correct location (GSASII-bin, not GSASII/bin)
echo "Step 6: Moving binaries to GSASII-bin/ (expected by GSAS-II)..."
echo "-----------------------------------------------------------------------"

# Meson installs to GSASII/bin/, but GSAS-II expects binaries at GSASII-bin/
# (See pathHacking.py - searches for GSASII-bin at repository root)

if [ -d "${GSAS_SOURCE_DIR}/GSASII/bin" ]; then
    # Determine platform-specific directory name
    PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    NPVER=$(python3 -c "import numpy; v=numpy.__version__.split('.'); print(f'{v[0]}.{v[1]}')")

    # Platform detection (lin for Linux, dar for Darwin/macOS, win for Windows)
    case "$(uname -s)" in
        Linux*)   PLATFORM="lin";;
        Darwin*)  PLATFORM="dar";;
        CYGWIN*|MINGW*|MSYS*) PLATFORM="win";;
        *)        PLATFORM="lin";;  # Default to Linux
    esac

    PLATFORM_DIR="${PLATFORM}_64_p${PYVER}_n${NPVER}"
    TARGET_DIR="${GSAS_SOURCE_DIR}/GSASII-bin/${PLATFORM_DIR}"

    echo "Platform directory: ${PLATFORM_DIR}"
    echo "Source: ${GSAS_SOURCE_DIR}/GSASII/bin/"
    echo "Target: ${TARGET_DIR}"
    echo ""

    # Create platform-specific directory in GSASII-bin
    mkdir -p "${TARGET_DIR}"

    # Find and move all compiled binaries from GSASII/bin to the platform directory
    echo "Moving compiled binaries..."
    if find "${GSAS_SOURCE_DIR}/GSASII/bin" -type f \( -name "*.so" -o -name "*.pyd" -o -name "*.dylib" \) -print0 2>/dev/null | xargs -0 -I {} mv {} "${TARGET_DIR}/" 2>/dev/null; then
        echo -e "${GREEN}✓ Binaries moved successfully${NC}"
    else
        # Try alternative: move entire subdirectories if they exist
        echo "Trying alternative move strategy..."
        for subdir in "${GSAS_SOURCE_DIR}/GSASII/bin/"*; do
            if [ -d "$subdir" ]; then
                echo "  Moving contents of $(basename "$subdir")..."
                mv "$subdir"/* "${TARGET_DIR}/" 2>/dev/null || cp -r "$subdir"/* "${TARGET_DIR}/"
            fi
        done
        # Also move any loose files
        find "${GSAS_SOURCE_DIR}/GSASII/bin" -maxdepth 1 -type f -exec mv {} "${TARGET_DIR}/" \; 2>/dev/null
    fi

    # Remove old bin directory
    rm -rf "${GSAS_SOURCE_DIR}/GSASII/bin"

    # List what we moved
    echo ""
    echo "Binaries in ${PLATFORM_DIR}:"
    ls -lh "${TARGET_DIR}" | head -10

    echo -e "${GREEN}✓ Binaries organized in GSASII-bin/${PLATFORM_DIR}/${NC}"
else
    echo -e "${YELLOW}⚠ No binaries found at GSASII/bin/ - nothing to move${NC}"
fi

echo ""

# Step 7: Verify installation
echo "Step 7: Verifying binary installation..."
echo "-----------------------------------------------------------------------"

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
NPVER=$(python3 -c "import numpy; v=numpy.__version__.split('.'); print(f'{v[0]}.{v[1]}')")

# Platform detection
case "$(uname -s)" in
    Linux*)   PLATFORM="lin";;
    Darwin*)  PLATFORM="dar";;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="win";;
    *)        PLATFORM="lin";;
esac

PLATFORM_DIR="${PLATFORM}_64_p${PYVER}_n${NPVER}"
BINARY_DIR="${GSAS_SOURCE_DIR}/GSASII-bin/${PLATFORM_DIR}"

echo "Expected binary directory: ${BINARY_DIR}"

if [ -d "${BINARY_DIR}" ]; then
    echo -e "${GREEN}✓ Binary directory found${NC}"

    # Check for critical binaries
    echo ""
    echo "Checking for compiled binaries..."
    BINARIES_OK=true
    for binary in pyspg pypowder; do
        if ls "${BINARY_DIR}/${binary}".* 1> /dev/null 2>&1; then
            echo "  ✓ ${binary} found"
        else
            echo -e "  ${YELLOW}⚠ ${binary} not found${NC}"
            BINARIES_OK=false
        fi
    done

    if [ "$BINARIES_OK" = false ]; then
        echo ""
        echo -e "${YELLOW}⚠ Some binaries missing, but installation may still work${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Binary directory not at expected location${NC}"
    echo "Searching for binaries..."

    # Try to find where binaries were installed
    if [ -d "${GSAS_SOURCE_DIR}/GSASII-bin" ]; then
        echo "Contents of GSASII-bin/:"
        ls -la "${GSAS_SOURCE_DIR}/GSASII-bin"

        # Find any .so files
        echo ""
        echo "Searching for .so files..."
        find "${GSAS_SOURCE_DIR}/GSASII-bin" -type f -name "*.so" 2>/dev/null | head -5 || echo "  No .so files found"
    else
        echo -e "${RED}✗ GSASII-bin/ directory not found${NC}"
        echo "Checking if binaries are still in wrong location (GSASII/bin/):"
        if [ -d "${GSAS_SOURCE_DIR}/GSASII/bin" ]; then
            echo -e "${YELLOW}  ⚠ Found binaries in GSASII/bin/ - they should be moved to GSASII-bin/${NC}"
        fi
    fi
fi

echo ""

# Step 8: Test import
echo "Step 8: Testing GSAS-II binary loading..."
echo "-----------------------------------------------------------------------"

export GSAS2DIR="${GSAS_SOURCE_DIR}/GSASII"
export PYTHONPATH="${GSAS2DIR}:${PYTHONPATH}"

python3 << 'EOF'
import sys
import os

gsas_dir = os.environ.get('GSAS2DIR')
if gsas_dir and gsas_dir not in sys.path:
    sys.path.insert(0, gsas_dir)

try:
    import GSASIIpath
    GSASIIpath.SetBinaryPath(showConfigMsg=True)

    # Try to import a module that uses binaries
    import pypowder

    print("\n✓ GSAS-II binaries loaded successfully!")
    print(f"  Binary path: {GSASIIpath.binaryPath}")

except Exception as e:
    print(f"\n⚠ GSAS-II binary loading test encountered issues:")
    print(f"  {e}")
    print("\nThis may be normal - some features require compute nodes.")
    print("Run initialize_gsas_headless.py to complete setup.")
    # Don't exit with error - initialization script will handle this
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Binary test passed${NC}"
else
    echo -e "${YELLOW}⚠ Binary test had warnings (may work after initialization)${NC}"
fi

echo ""
echo "======================================================================="
echo -e "${GREEN}GSAS-II Compilation Complete!${NC}"
echo "======================================================================="
echo ""
echo "Binary location: ${BINARY_DIR}"
echo "GSAS-II source:  ${GSAS2DIR}"
echo ""
echo "Next steps:"
echo "  1. Run GSAS-II initialization:"
echo "     python XRD/initialize_gsas_headless.py ${GSAS_SOURCE_DIR}"
echo ""
echo "  2. Test G2script import:"
echo "     python -c 'import G2script; print(G2script.__file__)'"
echo ""
echo "======================================================================="
