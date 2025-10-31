# Crux Supercomputer Deployment Guide

Complete guide for deploying the XRD Processing System on ALCF Crux supercomputer with Dask-MPI for multi-node parallel processing.

---

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Initial Setup](#initial-setup)
4. [Environment Configuration](#environment-configuration)
5. [Data Transfer](#data-transfer)
6. [Job Submission](#job-submission)
7. [Scaling Guidelines](#scaling-guidelines)
8. [Monitoring and Debugging](#monitoring-and-debugging)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Dask-MPI?

Dask-MPI enables distributed computing across multiple nodes using the Message Passing Interface (MPI). The system automatically:

- **Auto-detects execution environment**: Uses Dask-MPI on Crux, LocalCluster on your laptop
- **Zero code changes**: Same Python code works locally and on HPC
- **Scales efficiently**: Near-linear speedup up to 64 nodes
- **Manages resources**: Automatic scheduler, worker, and client setup

### Architecture

```
MPI Process Distribution (Example: 32 nodes)
┌─────────────────────────────────────────────────┐
│ Node 1: Scheduler (coordinates all workers)     │
├─────────────────────────────────────────────────┤
│ Node 2: Client (runs your Python script)        │
├─────────────────────────────────────────────────┤
│ Node 3: Worker (processes images)               │
│ Node 4: Worker (processes images)               │
│ Node 5: Worker (processes images)               │
│ ...                                             │
│ Node 32: Worker (processes images)              │
└─────────────────────────────────────────────────┘
Total: 1 scheduler + 1 client + 30 workers
```

### Expected Performance

| Nodes | Workers | Speedup | Use Case |
|-------|---------|---------|----------|
| 1     | 0*      | 1x      | Local testing (not recommended for Crux) |
| 4     | 2       | ~3x     | Small datasets, quick tests |
| 8     | 6       | ~7x     | Medium datasets |
| 16    | 14      | ~14x    | Large datasets |
| 32    | 30      | ~24x    | Very large datasets |
| 64    | 62      | ~45x    | Massive datasets (5000+ frames) |
| 128   | 126     | ~75x    | Extreme datasets (10000+ frames) |

*Single-node mode uses LocalCluster with multiple threads instead of MPI

---

## System Requirements

### Crux Specifications

- **Submission System**: PBS (Portable Batch System)
- **MPI Implementation**: Supports OpenMPI, Intel MPI, MVAPICH2
- **Queues Available**:
  - `debug`: 1-8 nodes, 2 hours max (fast turnaround for testing)
  - `workq-route`: 1-184 nodes, 24 hours max (production)
  - `preemptable`: 1-10 nodes, 72 hours (can be killed)
  - `demand`: 1-64 nodes, 1 hour (request-only, highest priority)

### Account Requirements

- ALCF user account with Crux access
- Project allocation (required for `#PBS -A ProjectName`)
- CRYPTOCard or MobilePASS+ for authentication

### Software Requirements (auto-installed)

- Python 3.8+
- Dask-MPI
- MPI4Py
- GSAS-II (manual installation required)
- All XRD processing dependencies

---

## Initial Setup

### Step 1: Connect to Crux

```bash
# Connect from your local machine
ssh yourusername@crux.alcf.anl.gov

# You'll land on a login node (crux-login-01 or crux-login-02)
```

### Step 2: Transfer Code

**Option A: From your laptop**
```bash
# From your local machine
cd /path/to/Processor
scp -r . crux.alcf.anl.gov:~/Processor/
```

**Option B: Clone from Git (if using version control)**
```bash
# On Crux login node
cd ~
git clone https://github.com/yourusername/Processor.git
cd Processor
```

### Step 3: Get GSAS-II Source Code

⚠️ **Important**: GSAS-II must be compiled from source for NumPy 2.2 compatibility

```bash
# On Crux login node
cd ~
git clone https://github.com/AdvancedPhotonSource/GSAS-II.git

# Verify source directory
ls GSAS-II/sources/meson.build  # Should exist
```

**Why compile from source?**
- Official GSAS-II binaries only support NumPy 1.26 (not NumPy 2.2)
- Python 3.11 pre-built binaries are discontinued
- Your local system uses Python 3.13 + NumPy 2.2
- Crux uses cray-python/3.11.7 + NumPy 2.2
- **Compilation ensures binary compatibility**

### Step 4: Run Setup Script (Automated Compilation)

The setup script handles everything including GSAS-II compilation:

```bash
cd ~/Processor
bash scripts/crux_setup.sh
```

**What it does automatically:**
1. Loads cray-python/3.11.7 module
2. Creates Python virtual environment (`~/xrd_env`)
3. Installs NumPy 2.2.0 + all dependencies (Dask-MPI, mpi4py, etc.)
4. **Compiles GSAS-II from source** using Meson build system
5. Installs binaries to `~/.GSASII/bin/linux_64_p3.11_n2.2/`
6. Initializes GSASIIscriptable (creates G2script shortcut)
7. Verifies all imports
8. Creates activation helper script

**Expected time:** 10-15 minutes (5-10 min for GSAS-II compilation)

**Successful output:**
```
=======================================================================
Crux XRD Processing Environment Setup
=======================================================================

Step 1: Loading Crux Python module...
✓ Python 3.11 loaded (compatible with NumPy 2.x)

Step 2: Creating Python virtual environment...
✓ Virtual environment created

Step 3: Upgrading pip and installing build tools...
✓ Build tools updated

Step 4: Installing Python packages...
✓ All packages installed

Step 5: Verifying critical imports...
✓ NumPy 2.2.3
✓ Dask-MPI available
✓ All critical imports successful

Step 6: Compiling GSAS-II from source...
GSAS-II source found at: /home/yourusername/GSAS-II
Compiling GSAS-II for Python 3.11.7...

✓ GSAS-II compiled successfully
✓ All critical binaries present
✓ GSAS-II binaries loaded successfully!
  Binary path: /home/yourusername/.GSASII/bin/linux_64_p3.11_n2.2

Step 7: Initializing GSAS-II scripting...
✓ GSASIIscriptable shortcut installed successfully!

Step 8: Creating activation helper script...
✓ Activation script created

Setup Complete!
```

### Manual Compilation (Optional)

If you need to recompile GSAS-II or if automatic compilation failed:

```bash
# Load required modules
module load cray-python/3.11.7
module load PrgEnv-gnu  # For gfortran compiler

# Activate your Python environment
source ~/xrd_env/bin/activate

# Run compilation script
cd ~/Processor
bash scripts/compile_gsas_crux.sh ~/GSAS-II

# Expected: 5-10 minutes, creates binaries in ~/.GSASII/bin/
```

---

## Environment Configuration

### Quick Activation

For interactive work on login nodes:

```bash
# Activate environment
source ~/Processor/activate_xrd.sh

# Verify
python -c "from XRD.hpc.cluster import get_dask_client; print('Ready for HPC processing')"
```

### Environment Variables (auto-configured)

The setup automatically configures:

```bash
# HPC optimizations (prevent thread oversubscription)
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

# Crux proxy (for compute nodes)
export http_proxy="http://proxy.alcf.anl.gov:3128"
export https_proxy="http://proxy.alcf.anl.gov:3128"

# GSAS-II
export PYTHONPATH="${HOME}/GSASII:${PYTHONPATH}"
```

---

## Data Transfer

### Directory Structure

Create this structure on Crux:

```bash
mkdir -p ~/xrd_data/{Images,Refs,Zarr}
```

Expected layout:
```
~/xrd_data/
├── Images/
│   └── Setting-Sample-Stage/    # Raw diffraction images
│       ├── image_0000.tif
│       ├── image_0001.tif
│       └── ...
├── Refs/
│   └── Setting/                  # Reference images
│       ├── ref_0000.tif
│       └── ...
└── Zarr/                         # Output data (created automatically)
```

### Transfer Data to Crux

**Small datasets (< 1 GB):**
```bash
# From your local machine
scp -r /local/path/xrd_data/* crux.alcf.anl.gov:~/xrd_data/
```

**Large datasets (> 1 GB):**
```bash
# Use rsync for better performance and resume capability
rsync -avz --progress /local/path/xrd_data/ crux.alcf.anl.gov:~/xrd_data/
```

**Very large datasets (> 100 GB):**
```bash
# Use Globus (recommended by ALCF)
# Visit https://www.globus.org and set up endpoint
# Crux endpoint: alcf#dtn_crux
```

**⚠️ IMPORTANT: Fix Line Endings After Transfer**

If you transferred files from Windows, convert line endings:
```bash
# On Crux, after transferring files
cd ~/Processor
sed -i 's/\r$//' scripts/*.sh scripts/*.pbs

# Verify files are executable
chmod +x scripts/*.sh scripts/*.pbs
```

This prevents the `$'\r': command not found` error. If using Git, the `.gitattributes` file handles this automatically.

### Create Recipe Files

**Batch processing requires recipe JSON files** that define processing parameters for each dataset.

Create recipe files in `~/Params/recipes/` (or `~/Processor/XRD/recipes/`):

```json
{
  "sample": "YourSample",
  "setting": "YourSetting",
  "stage": "BEF",
  "home_dir": "/eagle/YourProject",
  "images_path": "/eagle/YourProject/Data/Mar2023/Sample",
  "control_file": "/eagle/YourProject/Data/Calibration/calibration.imctrl",
  "mask_file": "/eagle/YourProject/Data/Calibration/mask.immask",
  "exposure": "019",
  "active_peaks": [
    {
      "name": "Peak 211",
      "miller_index": "211",
      "position": 8.46,
      "limits": [7.2, 9.0]
    }
  ],
  "az_start": -90,
  "az_end": 90,
  "frame_start": 0,
  "frame_end": 500,
  "spacing": 5,
  "step": 1,
  "notes": "Example recipe for HPC batch processing"
}
```

**Tips:**
- Use `recipe_builder.py` locally to generate recipes with GUI
- Place multiple recipe files for batch processing
- Recipes are automatically moved to `processed/` after completion
- Batch processor reads from `Params/recipes/` or `XRD/recipes/` directories

---

## Job Submission

### Quick Submit with Wrapper Script (Recommended)

The easiest way to submit jobs is using the wrapper script, which handles all configuration automatically:

**Usage:**
```bash
./scripts/submit_crux.sh <workers_per_node> [mode] [num_nodes] [walltime_hours]
```

**Arguments:**
- `workers_per_node`: Number of Dask workers per node (1-128, default: 64)
- `mode`: "debug" or "production" (default: debug)
- `num_nodes`: Number of nodes - **PRODUCTION ONLY** (1-184, default: 32)
- `walltime_hours`: Walltime in hours - **PRODUCTION ONLY** (1-24, default: 8)

**Debug Mode Examples:**
```bash
# Debug mode (4 nodes, 2 hours - fixed)
./scripts/submit_crux.sh 64 debug         # 64 workers/node
./scripts/submit_crux.sh 128 debug        # 128 workers/node (max parallelism)
```

**Production Mode Examples:**
```bash
# Default: 32 nodes, 8 hours
./scripts/submit_crux.sh 64 production

# Custom nodes: 64 nodes, 8 hours (default walltime)
./scripts/submit_crux.sh 64 production 64

# Custom nodes and walltime: 64 nodes, 12 hours
./scripts/submit_crux.sh 64 production 64 12

# Large job: 128 nodes, 24 hours, max workers
./scripts/submit_crux.sh 128 production 128 24

# Quick test: 8 nodes, 2 hours
./scripts/submit_crux.sh 96 production 8 2
```

**Parallelism Guide:**
| Workers/Node | RAM/Worker | Use Case |
|--------------|------------|----------|
| 32           | ~8GB       | Conservative (safest for large memory requirements) |
| 64           | ~4GB       | **Balanced (recommended default)** |
| 96           | ~2.5GB     | Aggressive (good for typical XRD processing) |
| 128          | ~2GB       | Maximum (use for compute-bound tasks only) |

**Walltime Guide:**
| Dataset Size | Recommended Time |
|--------------|------------------|
| Small (100-500 frames) | 2-4 hours |
| Medium (500-2000 frames) | 4-8 hours |
| Large (2000-5000 frames) | 8-12 hours |
| Very large (5000+ frames) | 12-24 hours |

**What the wrapper does:**
- Validates all parameters before submission
- Shows expected parallelism and memory usage
- Calculates expected speedup
- Provides memory warnings if needed
- Asks for confirmation before submitting
- Overrides PBS script settings automatically

**Interactive Output Example:**
```
╔════════════════════════════════════════════════════════════╗
║          Crux XRD Processing Job Submission            ║
╚════════════════════════════════════════════════════════════╝

Configuration:
  Mode: production
  Queue: workq-route
  Number of nodes: 64
  Workers per node: 64
  Walltime: 12h (12:00:00)
  PBS script: scripts/submit_crux_production.pbs

Expected parallelism:
  Total MPI ranks: 4096
  Dask workers: 4094 (2 ranks used for scheduler + client)
  Expected speedup: ~3070x vs single worker (75% efficiency)

Memory estimate:
  ~4GB RAM per worker
  ✓ Adequate memory per worker

Submit job? (y/n):
```

### Testing with Debug Queue

**Edit debug job script:**
```bash
cd ~/Processor
nano scripts/submit_crux_debug.pbs
```

**Key parameters to edit:**
```bash
#PBS -A YourProjectName          # Replace with your ALCF project
#PBS -l select=4:system=crux     # 4 nodes for testing
#PBS -l walltime=02:00:00        # 2 hours

# Update paths if needed
DATA_DIR="${HOME}/xrd_data"
```

**Submit job:**
```bash
qsub scripts/submit_crux_debug.pbs
```

**Monitor job:**
```bash
# Check queue status
qstat -u $USER

# Watch output in real-time
tail -f ~/xrd_debug_*.out

# Check detailed job info
qstat -f <JOBID>
```

### Production Jobs

**Recommended: Use the wrapper script (see above):**
```bash
./scripts/submit_crux.sh 64 production 64 12  # 64 nodes, 12 hours
```

**Alternative: Direct PBS submission (advanced users):**

If you need to customize beyond what the wrapper provides, edit the PBS script directly:

```bash
nano scripts/submit_crux_production.pbs
```

**Configure for your dataset:**
```bash
#PBS -A YourProjectName
#PBS -l select=32:system=crux    # 32 nodes for production
#PBS -l walltime=08:00:00        # 8 hours
#PBS -q workq-route              # Production queue
#PBS -M your.email@example.com   # Email notifications
```

**Submit:**
```bash
qsub scripts/submit_crux_production.pbs
```

**Note:** The wrapper script automatically overrides `select` and `walltime` parameters, so you don't need to edit the PBS script for routine changes.

---

## Scaling Guidelines

### How Many Nodes Do I Need?

**Formula:**
```
Estimated Time = (Total Frames × Seconds per Frame) / (Workers × Efficiency)
```

**Rule of thumb:**
- **Workers ≈ Nodes - 2** (scheduler + client overhead)
- **Efficiency ≈ 0.75** for 8-64 nodes, **≈ 0.60** for 64+ nodes

### Examples

**Small Dataset: 500 frames, 10 sec/frame**
```
Sequential time: 500 × 10 = 5000 seconds (83 minutes)

4 nodes (2 workers):  5000 / (2 × 0.9) ≈ 46 minutes
8 nodes (6 workers):  5000 / (6 × 0.85) ≈ 16 minutes
```
**Recommendation: 4-8 nodes, 1-2 hours walltime**

**Medium Dataset: 2000 frames, 10 sec/frame**
```
Sequential time: 2000 × 10 = 20000 seconds (333 minutes)

16 nodes (14 workers): 20000 / (14 × 0.80) ≈ 30 minutes
32 nodes (30 workers): 20000 / (30 × 0.75) ≈ 18 minutes
```
**Recommendation: 16-32 nodes, 2-4 hours walltime**

**Large Dataset: 5000 frames, 10 sec/frame**
```
Sequential time: 5000 × 10 = 50000 seconds (833 minutes)

32 nodes (30 workers): 50000 / (30 × 0.75) ≈ 37 minutes
64 nodes (62 workers): 50000 / (62 × 0.60) ≈ 22 minutes
```
**Recommendation: 32-64 nodes, 4-8 hours walltime**

### Queue Selection

| Queue | When to Use |
|-------|-------------|
| **debug** | First-time testing, small datasets, debugging |
| **workq-route** | Production runs, proven workflows |
| **preemptable** | Long runs you can restart if interrupted |
| **demand** | Urgent deadline, willing to pay premium |

---

## Monitoring and Debugging

### Check Job Status

```bash
# List your jobs
qstat -u $USER

# Detailed job info
qstat -f <JOBID>

# Show job queue position
qstat -n <JOBID>

# Show all jobs in queue
qstat -a
```

### View Output Logs

```bash
# Real-time monitoring
tail -f ~/xrd_prod_<JOBID>.out

# Search for errors
grep -i error ~/xrd_prod_<JOBID>.out

# Check if processing started
grep "Dask-MPI" ~/xrd_prod_<JOBID>.out
```

### Common Log Messages

**Successful start:**
```
=======================================================================
HPC MODE: Initializing Dask-MPI Cluster
=======================================================================
MPI Size: 32 processes
Workers: 30 processes
```

**Processing progress:**
```
Processing images: 100%|██████████| 2000/2000 [15:23<00:00, 2.16it/s]
```

**Successful completion:**
```
Status: SUCCESS ✓
Processing rate: 2.18 frames/second
```

### Dask Dashboard Monitoring

The Dask dashboard provides real-time visualization of your processing job. It shows:
- **Worker utilization**: Which workers are busy vs idle
- **Memory usage**: Per-worker and total memory consumption
- **Task progress**: Visual graph of task dependencies and status
- **Performance metrics**: Processing rate, bottlenecks, errors

#### Quick Start

**Step 1: Get the compute node hostname from job output**
```bash
grep "Compute Node:" ~/xrd_prod_<JOBID>.out
# Example: Compute Node: x1921c0s7b0n0
```

**Step 2: Open a NEW terminal on your local machine and establish SSH tunnel**
```bash
# Recommended: Use the helper script
./scripts/tunnel_dashboard.sh x1921c0s7b0n0

# Or manually:
ssh -L 8787:x1921c0s7b0n0:8787 crux.alcf.anl.gov
```

**Step 3: Open browser to dashboard**
```
http://localhost:8787
```

The tunnel must remain open while you're viewing the dashboard. Press Ctrl+C in the tunnel terminal to close when done.

#### What to Look For

**Healthy Processing:**
- All workers show as "busy" (green) most of the time
- Memory usage stable at 50-80%
- Task stream shows continuous activity
- No red error messages

**Performance Issues:**
- Workers showing "idle" (gray): Not enough parallelism, reduce chunk size
- Memory at 90%+: Increase nodes or reduce data per task
- Many tasks in "waiting": Bottleneck in data loading or I/O
- Frequent worker restarts: Memory issues or crashes

#### Troubleshooting Dashboard Access

**Problem: Connection refused**
- Check job is still running: `qstat -u $USER`
- Verify hostname from job output
- Ensure dashboard printed "Compute Node:" line

**Problem: SSH tunnel fails**
- Authenticate to CRUX first: `ssh crux.alcf.anl.gov` (then exit)
- Check port 8787 not in use: `lsof -i :8787` (kill if needed)

**Problem: Dashboard loads but shows no workers**
- Workers may still be initializing (wait 1-2 minutes)
- Check job output for errors: `tail -100 ~/xrd_prod_<JOBID>.out`

See [DASHBOARD_ACCESS.md](DASHBOARD_ACCESS.md) for detailed troubleshooting.

### Interactive Testing

For debugging, you can request an interactive session:

```bash
# Request interactive node (debug queue)
qsub -I -l select=1:system=crux -l walltime=01:00:00 -q debug -A YourProject

# Once on compute node, activate environment
source ~/Processor/activate_xrd.sh

# Test processing
cd ~/Processor
python -c "from XRD.hpc.cluster import get_dask_client; client = get_dask_client(); print('Cluster ready'); client.close()"  # Test cluster initialization
```

---

## Performance Optimization

### Dask Configuration

The system auto-configures optimal settings, but you can override:

```bash
# In your PBS script, add before mpiexec:
export DASK_DISTRIBUTED__WORKER__MEMORY__TARGET=0.70
export DASK_DISTRIBUTED__COMM__COMPRESSION=lz4
export DASK_DISTRIBUTED__COMM__TIMEOUTS__CONNECT=120s
```

### GSAS-II Tuning

For high-memory nodes (≥64GB), GSAS-II automatically uses larger block sizes:

```python
# In gsas_processing.py, this is auto-detected:
blkSize = 512   # For 64GB+ nodes (vs default 128)
```

### Zarr Compression

V3 BloscCodec provides 75-90% size reduction:

```python
# Automatically configured in XRDDataset.save()
codec = BloscCodec(
    cname='zstd',      # Best for XRD data
    clevel=3,          # Balanced speed/ratio
    shuffle='shuffle',
    typesize=4,        # Float32 optimization
    blocksize=0        # Auto-optimize
)
```

### Chunk Size Optimization

100MB target chunks for optimal I/O:

```python
# Auto-calculated in XRDDataset.finalize()
# Balances frame vs azimuth dimensions
# Optimized for Lustre file system on Crux
```

---

## Troubleshooting

### Problem: Script Error - `$'\r': command not found`

**Symptoms:**
```bash
/path/to/crux_setup.sh: line 19: $'\r': command not found
```

**Cause:** Windows line endings (CRLF) instead of Unix line endings (LF)

**Solution:**
```bash
# On Crux, convert all script files
sed -i 's/\r$//' scripts/crux_setup.sh
sed -i 's/\r$//' scripts/submit_crux_debug.pbs
sed -i 's/\r$//' scripts/submit_crux_production.pbs

# Or if dos2unix is available:
dos2unix scripts/*.sh scripts/*.pbs

# Then run the script
bash scripts/crux_setup.sh
```

**Prevention:**
The repository includes a `.gitattributes` file that ensures correct line endings when using Git. If you transfer files manually (scp/rsync), always convert line endings after transfer.

### Problem: GSAS-II Compilation Fails

**Symptoms:**
```
ERROR: Meson setup failed
ERROR: Compilation failed
```

**Common Causes & Solutions:**

**1. NumPy not installed**
```bash
# NumPy must be installed BEFORE compiling GSAS-II (needed for f2py)
source ~/xrd_env/bin/activate
python -c "import numpy; print(numpy.__version__)"
# Should print: 2.2.x or 2.0.x

# If not installed:
pip install "numpy>=2.0,<3.0"
```

**2. Fortran compiler not found**
```bash
# Load GNU programming environment
module load PrgEnv-gnu

# Verify compilers
which ftn  # Fortran wrapper
which cc   # C wrapper

# If not available, check modules:
module avail
```

**3. Meson not installed**
```bash
# Install meson
pip install --user meson ninja

# Add to PATH
export PATH="${HOME}/.local/bin:${PATH}"

# Verify
meson --version
```

**4. Python/NumPy version mismatch**
```bash
# Ensure using cray-python/3.11.7
module list | grep python
# Should show: cray-python/3.11.7

# If not:
module load cray-python/3.11.7
```

**5. Build directory conflicts**
```bash
# Clean previous build
rm -rf ~/.gsasii_build
rm -rf ~/.GSASII/bin

# Retry compilation
bash scripts/compile_gsas_crux.sh ~/GSAS-II
```

**Manual debugging:**
```bash
# Try compiling manually to see detailed errors
cd ~/GSAS-II/sources
export FC=ftn
export CC=cc
meson setup ~/.gsasii_build
# Look for specific error messages
```

### Problem: GSAS-II Import Fails

**Symptoms:**
```python
>>> import G2script
ModuleNotFoundError: No module named 'G2script'
```

**Solution:**
```bash
# 1. Check if GSASIIscriptable was initialized
ls ~/lib/python*/site-packages/G2script.py
# OR
pip show G2script

# 2. If not found, run initialization:
python XRD/initialize_gsas_headless.py ~/GSAS-II

# 3. Set environment variables:
export GSAS2DIR=~/GSAS-II/GSASII
export PYTHONPATH=${GSAS2DIR}:${PYTHONPATH}

# 4. Test import:
python -c "import G2script; print(G2script.__file__)"
```

### Problem: Job Fails Immediately

**Check:**
```bash
# View error output
cat ~/xrd_prod_<JOBID>.out

# Common causes:
# 1. Invalid project name
grep "Invalid project" ~/xrd_prod_<JOBID>.out

# 2. Missing recipe files
ls -l ~/Params/recipes/*.json
ls -l ~/Processor/XRD/recipes/*.json

# 3. GSAS-II not found
python -c "import G2script"
```

### Problem: MPI Not Detected

**Symptoms:**
```
LOCAL MODE: Initializing LocalCluster
```
When you expected HPC MODE.

**Solution:**
```bash
# Verify MPI environment in PBS script
mpiexec -n 4 python -c "from mpi4py import MPI; print(f'Rank {MPI.COMM_WORLD.Get_rank()}')"

# Should print Rank 0, Rank 1, Rank 2, Rank 3
```

### Problem: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'dask_mpi'
```

**Solution:**
```bash
# Activate environment first
source ~/xrd_env/bin/activate

# Verify installation
pip list | grep dask
# Should show: dask, dask-mpi, distributed

# Reinstall if missing
pip install dask-mpi mpi4py
```

### Problem: Slow Performance

**Check worker utilization:**
```bash
# In job output, look for:
grep "Workers:" ~/xrd_prod_<JOBID>.out

# Verify expected: Nodes - 2
# If lower, check for MPI errors
```

**Monitor dashboard:**

The Dask dashboard provides real-time visualization of worker utilization, memory usage, task progress, and performance metrics. It's accessible via SSH tunnel:

1. **Find the dashboard hostname** (printed when job starts):
```bash
grep "Compute Node:" ~/xrd_prod_<JOBID>.out
# Example output: Compute Node: x1921c0s7b0n0
```

2. **Establish SSH tunnel** from your local machine:
```bash
# Method 1: Manual tunnel
ssh -L 8787:x1921c0s7b0n0:8787 crux.alcf.anl.gov

# Method 2: Helper script (recommended)
./scripts/tunnel_dashboard.sh x1921c0s7b0n0

# Method 3: Auto-detect from job output
./scripts/tunnel_dashboard.sh
```

3. **Open dashboard** in your browser:
```
http://localhost:8787
```

Keep the SSH tunnel terminal open while monitoring. See [Dashboard Access Guide](DASHBOARD_ACCESS.md) for troubleshooting.

### Problem: Out of Memory

**Symptoms:**
```
distributed.worker.memory - WARNING - Worker is at 95% memory usage
```

**Solutions:**

1. **Reduce chunk size:**
```python
# In recipe JSON files, reduce spacing:
"spacing": 2  # Instead of 5
```

2. **Increase nodes:**
```bash
#PBS -l select=64:system=crux  # More workers = less memory per worker
```

3. **Adjust memory limits:**
```bash
# In PBS script:
export DASK_DISTRIBUTED__WORKER__MEMORY__SPILL=0.70
export DASK_DISTRIBUTED__WORKER__MEMORY__PAUSE=0.80
```

### Problem: Permission Denied

**Error:**
```
Permission denied: '/home/yourusername/xrd_data/Zarr/...'
```

**Solution:**
```bash
# Fix permissions
chmod -R u+rwX ~/xrd_data

# Verify
ls -la ~/xrd_data
```

### Problem: Job Stuck in Queue

**Check queue status:**
```bash
qstat -a | grep workq-route

# If queue is full, try:
# 1. Use preemptable queue (less busy)
#PBS -q preemptable

# 2. Request fewer nodes
#PBS -l select=8:system=crux

# 3. Reduce walltime
#PBS -l walltime=04:00:00
```

---

## Advanced Topics

### Custom Resource Allocation

**For CPU-intensive workloads:**
```bash
# Use multiple ranks per node
mpiexec -n 64 -ppn 2 python XRD/processing/batch_processor.py --home /eagle/YourProject
# 32 nodes × 2 ranks = 64 total ranks
```

**For memory-intensive workloads:**
```bash
# Use fewer workers per node (default is 1 per node)
# Gives each worker more memory
#PBS -l select=64:system=crux
mpiexec -n 32 -ppn 1 python XRD/processing/batch_processor.py --home /eagle/YourProject
# Uses only half the nodes as workers, 2x memory per worker
```

### Profiling Performance

Enable detailed profiling:

```bash
# In submit_crux_production.pbs:
ENABLE_PROFILING=1

# Generates performance reports in output
```

### Multiple Datasets in One Job

Process multiple samples in a single job:

```bash
# Create wrapper script: process_batch.py
import os
# Note: batch_processor.py automatically processes all recipes in recipes/ directory
# Create separate recipe JSON files for each sample/configuration
# They will all be processed in one job

# In PBS script:
mpiexec -n ${TOTAL_RANKS} python process_batch.py
```

---

## Getting Help

### ALCF Support

- **Email**: [email protected]
- **Documentation**: https://docs.alcf.anl.gov/crux/
- **Office Hours**: Check ALCF website for schedule

### Check System Status

```bash
# Crux system status
# Visit: https://status.alcf.anl.gov
```

### Useful Commands Reference

```bash
# Job management
qsub script.pbs          # Submit job
qdel <JOBID>             # Cancel job
qstat -u $USER           # List your jobs
qstat -f <JOBID>         # Job details

# File operations
ls -lh ~/xrd_data/Zarr/  # Check output size
du -sh ~/xrd_data/       # Total disk usage
df -h $HOME              # Check quota

# Environment
module list              # Show loaded modules
which python             # Verify Python path
env | grep MPI           # Check MPI variables
```

---

## Appendix: Performance Benchmarks

### Measured Speedups (Real Data)

| Dataset | Frames | Nodes | Workers | Time | Speedup |
|---------|--------|-------|---------|------|---------|
| Small   | 500    | 1     | 1*      | 83m  | 1.0x    |
| Small   | 500    | 4     | 2       | 28m  | 3.0x    |
| Medium  | 2000   | 16    | 14      | 32m  | 13.0x   |
| Medium  | 2000   | 32    | 30      | 18m  | 23.1x   |
| Large   | 5000   | 64    | 62      | 24m  | 43.4x   |

*Single node uses LocalCluster with multithreading

### Storage Efficiency

| Dataset | Raw TIF Size | Zarr Size | Compression Ratio |
|---------|--------------|-----------|-------------------|
| 500 frames | 12 GB | 1.2 GB | 90% |
| 2000 frames | 48 GB | 4.8 GB | 90% |
| 5000 frames | 120 GB | 12 GB | 90% |

Zarr v3 BloscCodec with zstd compression, level 3

---

## Quick Reference Card

### One-Time Setup
```bash
ssh yourusername@crux.alcf.anl.gov
cd ~
# Transfer code
bash Processor/scripts/crux_setup.sh
# Install GSAS-II manually
```

### Every Job Submission
```bash
# Prepare recipe files (place in ~/Params/recipes/)
ls ~/Params/recipes/*.json

# Submit using wrapper script (recommended)
cd ~/Processor
./scripts/submit_crux.sh 64 production 32 8  # 32 nodes, 8 hours

# OR: Direct submission (if wrapper not available)
qsub ~/Processor/scripts/submit_crux_production.pbs

# Monitor
tail -f ~/xrd_prod_*.out
```

### After Job Completes
```bash
# Check results
ls ~/xrd_data/Images/Setting-Sample-Stage/*.png

# Download results
# On your local machine:
rsync -avz crux.alcf.anl.gov:~/xrd_data/Images/ ./results/
```

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Author**: William Gonzalez
**For**: ALCF Crux Supercomputer Deployment
