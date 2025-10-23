#!/bin/bash
################################################################################
# Crux Supercomputer Environment Setup Script
# ===========================================
# Sets up Python environment for XRD processing on ALCF Crux system
#
# Usage:
#   bash scripts/crux_setup.sh
#
# This script:
# - Creates Python virtual environment with all dependencies
# - Installs optimized packages for HPC execution
# - Configures environment for Dask-MPI parallel processing
# - Provides instructions for GSAS-II installation
#
# Author: William Gonzalez
# Date: January 2025
################################################################################

set -e  # Exit on error

echo "======================================================================="
echo "Crux XRD Processing Environment Setup"
echo "======================================================================="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESSOR_DIR="$(dirname "${SCRIPT_DIR}")"
SOFTWARE_DIR="$(dirname "${PROCESSOR_DIR}")"
VENV_NAME="venv"
VENV_PATH="${SOFTWARE_DIR}/${VENV_NAME}"

echo "Detected paths:"
echo "  Software directory: ${SOFTWARE_DIR}"
echo "  PRISMA directory: ${PROCESSOR_DIR}"
echo "  VEnv location: ${VENV_PATH}"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Crux
if [[ $(hostname) != crux-login-* ]]; then
    echo -e "${YELLOW}WARNING: Not running on Crux login node${NC}"
    echo "Hostname: $(hostname)"
    echo "This script is optimized for ALCF Crux. Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

echo "Step 1: Loading Crux Python module..."
echo "-----------------------------------------------------------------------"

# Load cray-python module (required for NumPy 2.x support)
echo "Loading cray-python/3.11.7..."
module load cray-python/3.11.7 2>&1 || {
    echo -e "${RED}ERROR: Failed to load cray-python/3.11.7${NC}"
    echo ""
    echo "Available Python modules:"
    module avail python 2>&1 | grep -i python || echo "  None found"
    echo ""
    echo "Please load an appropriate Python 3.10+ module before running this script."
    exit 1
}

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo ${PYTHON_VERSION} | cut -d. -f1)
PYTHON_MINOR=$(echo ${PYTHON_VERSION} | cut -d. -f2)

echo "Detected Python version: ${PYTHON_VERSION}"

if [ "${PYTHON_MAJOR}" -lt 3 ] || [ "${PYTHON_MINOR}" -lt 10 ]; then
    echo -e "${RED}ERROR: Python 3.10+ required (GSAS-II needs NumPy 2.x)${NC}"
    echo "Current version: ${PYTHON_VERSION}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3.${PYTHON_MINOR} loaded (compatible with NumPy 2.x)${NC}"
echo ""

echo "Step 2: Creating Python virtual environment..."
echo "-----------------------------------------------------------------------"

if [ ! -d "${VENV_PATH}" ]; then
    echo "Creating virtual environment at: ${VENV_PATH}"
    python3 -m venv "${VENV_PATH}"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists at: ${VENV_PATH}${NC}"
    echo "Do you want to recreate it? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "${VENV_PATH}"
        python3 -m venv "${VENV_PATH}"
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    fi
fi

# Activate virtual environment
source "${VENV_PATH}/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo "Step 3: Upgrading pip and installing build tools..."
echo "-----------------------------------------------------------------------"
pip install --upgrade pip setuptools wheel
echo -e "${GREEN}✓ Build tools updated${NC}"
echo ""

echo "Step 4: Installing Python packages..."
echo "-----------------------------------------------------------------------"

# Core dependencies (from initialize.py + HPC additions)
# NumPy 1.26 required for GSAS-II compatibility
PACKAGES=(
    "numpy==1.26"
    "cython"
    "pybind11"
    "pandas"
    "scipy"
    "matplotlib"
    "seaborn"
    "imageio"
    "tqdm"
    "openpyxl"
    "pybaselines"
    "bokeh"
    # Dask ecosystem with MPI support
    "dask[distributed]"
    "dask-mpi"
    "mpi4py"
    # Zarr with v3 support and compression
    "zarr[v3]"
    "numcodecs>=0.12.0"
    # Performance monitoring
    "threadpoolctl"
    "psutil"
    # Multi-frame image support
    "fabio"
)

echo "Installing ${#PACKAGES[@]} packages..."
for package in "${PACKAGES[@]}"; do
    echo "  - Installing ${package}..."
    pip install "${package}" || {
        echo -e "${RED}✗ Failed to install ${package}${NC}"
        echo "Continue with remaining packages? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    }
done

echo -e "${GREEN}✓ All packages installed${NC}"
echo ""

echo "Step 5: Verifying critical imports..."
echo "-----------------------------------------------------------------------"

python3 << 'EOF'
import sys
print("Python version:", sys.version)
print()

# Test critical imports
imports = {
    "numpy": "NumPy",
    "pandas": "Pandas",
    "dask": "Dask",
    "dask.distributed": "Dask Distributed",
    "dask_mpi": "Dask-MPI",
    "mpi4py": "MPI4Py",
    "zarr": "Zarr",
    "numcodecs": "NumCodecs",
    "fabio": "FabIO",
    "matplotlib": "Matplotlib",
    "psutil": "PSUtil",
}

all_ok = True
for module, name in imports.items():
    try:
        __import__(module)
        print(f"✓ {name:20s} OK")
    except ImportError as e:
        print(f"✗ {name:20s} FAILED: {e}")
        all_ok = False

if all_ok:
    print("\n✓ All critical imports successful")
else:
    print("\n✗ Some imports failed - check installation")
    sys.exit(1)

# Check Zarr v3 codec support
try:
    from zarr.codecs import BloscCodec
    print("\n✓ Zarr v3 BloscCodec available (optimal compression)")
except ImportError:
    print("\n⚠ Zarr v3 codecs not available - will use v2 fallback")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All verifications passed${NC}"
else
    echo -e "${RED}✗ Verification failed${NC}"
    exit 1
fi
echo ""

echo "Step 6: Compiling GSAS-II from source..."
echo "-----------------------------------------------------------------------"

# Default GSAS-II location (same level as PRISMA)
GSAS_DIR="${SOFTWARE_DIR}/GSAS-II"

# Check if GSAS-II source exists
if [ -d "${GSAS_DIR}" ]; then
    echo "GSAS-II source found at: ${GSAS_DIR}"
    echo "Compiling GSAS-II for Python ${PYTHON_VERSION}..."
    echo ""

    # Run compilation script
    bash "${PROCESSOR_DIR}/scripts/compile_gsas_crux.sh" "${GSAS_DIR}" || {
        echo -e "${RED}✗ GSAS-II compilation failed${NC}"
        echo ""
        echo "You can try compiling manually later:"
        echo "  bash scripts/compile_gsas_crux.sh /path/to/GSAS-II"
        echo ""
        echo "Continue without GSAS-II? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    }
else
    echo -e "${YELLOW}GSAS-II source not found at: ${GSAS_DIR}${NC}"
    echo ""
    echo "To download GSAS-II:"
    echo "  cd ~"
    echo "  git clone https://github.com/AdvancedPhotonSource/GSAS-II.git"
    echo ""
    echo "After downloading, run the compilation script:"
    echo "  bash scripts/compile_gsas_crux.sh ~/GSAS-II"
    echo ""
    echo "Continue without GSAS-II compilation? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

echo "Step 7: Initializing GSAS-II scripting..."
echo "-----------------------------------------------------------------------"

# Only run if GSAS-II was compiled or exists
if [ -d "${GSAS_DIR}/GSASII" ]; then
    echo "Running headless GSAS-II initialization..."
    python3 "${PROCESSOR_DIR}/XRD/initialize_gsas_headless.py" "${GSAS_DIR}" || {
        echo -e "${YELLOW}⚠ GSAS-II initialization skipped or failed${NC}"
        echo "You can run this manually later:"
        echo "  python XRD/initialize_gsas_headless.py ${GSAS_DIR}"
    }
else
    echo -e "${YELLOW}⚠ GSAS-II not available - skipping initialization${NC}"
fi

echo ""

echo "Step 8: Creating activation helper script..."
echo "-----------------------------------------------------------------------"

# Create activation script
ACTIVATE_SCRIPT="${PROCESSOR_DIR}/activate_xrd.sh"
cat > "${ACTIVATE_SCRIPT}" << ACTIVATE_EOF
#!/bin/bash
# Quick activation script for XRD environment on Crux

# Determine directories
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
SOFTWARE_DIR="\$(dirname "\${SCRIPT_DIR}")"

# Load cray-python module
module load cray-python/3.11.7

# Activate virtual environment
source "\${SOFTWARE_DIR}/venv/bin/activate"

# GSAS-II environment
export GSAS2DIR="\${SOFTWARE_DIR}/GSAS-II/GSASII"
export PYTHONPATH="\${GSAS2DIR}:\${PYTHONPATH}"

# Crux proxy settings (for compute nodes)
export http_proxy="http://proxy.alcf.anl.gov:3128"
export https_proxy="http://proxy.alcf.anl.gov:3128"

# HPC optimizations (prevent thread oversubscription)
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

echo "XRD environment activated"
echo "Python: $(which python) ($(python --version))"
echo "GSAS-II: ${GSAS2DIR}"
ACTIVATE_EOF

chmod +x "${ACTIVATE_SCRIPT}"
echo -e "${GREEN}✓ Activation script created: ${ACTIVATE_SCRIPT}${NC}"
echo ""

echo "======================================================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================================================="
echo ""
echo "Summary:"
echo "  Python: ${PYTHON_VERSION} (cray-python/3.11.7)"
echo "  Virtual environment: ${VENV_PATH}"
echo "  GSAS-II: ${GSAS_DIR}"
echo "  Activation script: ${ACTIVATE_SCRIPT}"
echo ""
echo "Next steps:"
echo ""
echo "1. Activate environment for interactive work:"
echo "   source ${ACTIVATE_SCRIPT}"
echo ""
echo "2. Test GSAS-II import:"
echo "   python -c 'import G2script; print(G2script.__file__)'"
echo ""
echo "3. Test Dask-MPI cluster initialization:"
echo "   python XRD/hpc_cluster.py"
echo ""
echo "4. Submit a test job to debug queue:"
echo "   qsub scripts/submit_crux_debug.pbs"
echo ""
echo "5. For production runs, edit and submit:"
echo "   nano scripts/submit_crux_production.pbs  # Update project name, nodes, etc."
echo "   qsub scripts/submit_crux_production.pbs"
echo ""
echo "Documentation:"
echo "  - Full guide: docs/CRUX_DEPLOYMENT.md"
echo "  - Quick start: CRUX_QUICKSTART.md"
echo ""
echo "======================================================================="
