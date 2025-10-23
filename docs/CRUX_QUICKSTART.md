# Crux Quick Start Guide - With GSAS-II Compilation

Complete setup guide for running XRD processing on ALCF Crux supercomputer.

---

## Prerequisites

- ALCF account with Crux access
- Project allocation name (for PBS `#PBS -A` directive)
- CRYPTOCard or MobilePASS+ for authentication

---

## Quick Setup (5 Steps)

### 1. SSH to Crux & Transfer Code

```bash
# From your local machine
ssh yourusername@crux.alcf.anl.gov

# Transfer code (choose one method):
# Method A: SCP
scp -r Processor/ crux.alcf.anl.gov:~/

# Method B: Git clone
cd ~
git clone https://github.com/yourusername/Processor.git
```

### 2. Get GSAS-II Source

```bash
# On Crux
cd ~
git clone https://github.com/AdvancedPhotonSource/GSAS-II.git

# Verify
ls GSAS-II/sources/meson.build  # Should exist
```

**Why download source?**
- GSAS-II must be compiled for NumPy 2.2 compatibility
- Official binaries only support NumPy 1.26
- Python 3.11 binaries are discontinued

### 3. Fix Line Endings (Windows Users Only)

```bash
cd ~/Processor
sed -i 's/\r$//' scripts/*.sh scripts/*.pbs
chmod +x scripts/*.sh scripts/*.pbs
```

### 4. Run One-Command Setup

```bash
cd ~/Processor
bash scripts/crux_setup.sh
```

**What happens automatically:**
1. Loads cray-python/3.11.7 ✓
2. Creates Python venv with NumPy 2.2 ✓
3. Installs dask-mpi, mpi4py, all dependencies ✓
4. **Compiles GSAS-II from source** (5-10 min) ✓
5. Initializes GSASIIscriptable ✓
6. Creates activation script ✓

**Expected time:** 10-15 minutes

**Success looks like:**
```
Step 6: Compiling GSAS-II from source...
✓ GSAS-II compiled successfully
✓ All critical binaries present
  Binary path: /home/yourusername/.GSASII/bin/linux_64_p3.11_n2.2

Step 7: Initializing GSAS-II scripting...
✓ GSASIIscriptable shortcut installed successfully!

Setup Complete!
```

### 5. Test Installation

```bash
# Activate environment
source ~/Processor/activate_xrd.sh

# Test imports
python -c "import G2script; print('GSAS-II OK')"
python -c "import dask_mpi; print('Dask-MPI OK')"
python -c "from hpc_cluster import get_dask_client; print('HPC cluster OK')"
```

---

## Submitting Jobs

### Quick Test (Debug Queue)

```bash
# Edit PBS script
cd ~/Processor
nano scripts/submit_crux_debug.pbs

# Change this line:
#PBS -A YourProjectName  → #PBS -A your_actual_project

# Submit
qsub scripts/submit_crux_debug.pbs

# Monitor
qstat -u $USER
tail -f ~/xrd_debug_*.out
```

### Production Run

```bash
# Edit production script
nano scripts/submit_crux_production.pbs

# Update:
#PBS -A YourProjectName        # Your ALCF project
#PBS -l select=32:system=crux  # Number of nodes (adjust as needed)
#PBS -l walltime=08:00:00      # Time limit
#PBS -M your.email@example.com # Email for notifications

# Submit
qsub scripts/submit_crux_production.pbs
```

---

## Common Issues & Quick Fixes

### ❌ Error: `numpy==2.2` not found

**Cause:** NumPy 2.2 doesn't exist (latest is 2.1.x)

**Fix:**
```bash
# Already fixed in updated scripts
# Uses: numpy>=2.0,<3.0
```

### ❌ Error: `$'\r': command not found`

**Cause:** Windows line endings

**Fix:**
```bash
cd ~/Processor
sed -i 's/\r$//' scripts/*.sh scripts/*.pbs
```

### ❌ Error: GSAS-II compilation failed

**Check:**
```bash
# 1. Is cray-python loaded?
module list | grep python  # Should show cray-python/3.11.7

# 2. Is NumPy installed?
python -c "import numpy; print(numpy.__version__)"  # Should be 2.x

# 3. Are compilers available?
which ftn  # Fortran compiler
which cc   # C compiler

# If not, load:
module load cray-python/3.11.7
module load PrgEnv-gnu
```

**Retry compilation:**
```bash
source ~/xrd_env/bin/activate
bash scripts/compile_gsas_crux.sh ~/GSAS-II
```

### ❌ Error: G2script import fails

**Fix:**
```bash
# Run initialization manually
python XRD/initialize_gsas_headless.py ~/GSAS-II

# Set environment
export GSAS2DIR=~/GSAS-II/GSASII
export PYTHONPATH=${GSAS2DIR}:${PYTHONPATH}

# Test
python -c "import G2script"
```

### ❌ Job stuck in queue

**Check queue status:**
```bash
qstat -a | grep debug  # or workq-route

# If queue is full, options:
# 1. Use different queue
# 2. Request fewer nodes
# 3. Reduce walltime
```

---

## Scaling Guide

### How Many Nodes?

**Rule of thumb:** Workers = Nodes - 2 (scheduler + client)

| Dataset Size | Nodes | Workers | Expected Time |
|--------------|-------|---------|---------------|
| 500 frames   | 4     | 2       | ~20-30 min    |
| 1000 frames  | 8     | 6       | ~25-35 min    |
| 2000 frames  | 16    | 14      | ~30-40 min    |
| 5000 frames  | 32    | 30      | ~35-45 min    |
| 10000 frames | 64    | 62      | ~40-50 min    |

**Efficiency:** ~75% for 8-64 nodes, ~60% for 64+ nodes

### Queue Selection

| Queue | Use When |
|-------|----------|
| **debug** | Testing, debugging (fast, 2hr max) |
| **workq-route** | Production (24hr max, most flexible) |
| **preemptable** | Long runs, can restart if killed |
| **demand** | Urgent, willing to pay premium |

---

## Data Transfer

### To Crux

```bash
# Small datasets (< 10 GB)
scp -r /local/xrd_data/ crux.alcf.anl.gov:~/xrd_data/

# Large datasets (> 10 GB) - use rsync
rsync -avz --progress /local/xrd_data/ crux.alcf.anl.gov:~/xrd_data/

# Very large (> 100 GB) - use Globus
# https://www.globus.org
# Endpoint: alcf#dtn_crux
```

### From Crux

```bash
# Download results
rsync -avz crux.alcf.anl.gov:~/xrd_data/Images/Setting-Sample-Stage/ ./results/

# Or just the heatmaps
scp 'crux.alcf.anl.gov:~/xrd_data/Images/*/*.png' ./plots/
```

---

## Environment Management

### Activate Environment

```bash
# Quick activation (includes all environment variables)
source ~/Processor/activate_xrd.sh

# Verify
python --version  # Should be 3.11.x
which python      # Should be ~/xrd_env/bin/python
```

### Add to .bashrc (Optional)

```bash
# Auto-load on login
echo "source ~/Processor/activate_xrd.sh" >> ~/.bashrc
```

---

## Configuration File

Create `~/Processor/XRD/submitted_values.json`:

```json
{
  "sample": "YourSample",
  "setting": "YourSetting",
  "stage": "BEF",
  "image_folder": "/home/yourusername/xrd_data",
  "control_file": "/home/yourusername/xrd_data/calibration.imctrl",
  "mask_file": "/home/yourusername/xrd_data/mask.immask",

  "active_peaks": [
    {
      "name": "Peak 211",
      "miller_index": "211",
      "position": 8.46,
      "limits": [7.2, 9.0]
    }
  ],

  "azimuths": [0, 360],
  "frames": [0, -1],
  "spacing": 5,
  "step": 1,

  "pixel_size": [172.0, 172.0],
  "wavelength": 0.240,
  "detector_size": [1475, 1679]
}
```

---

## Complete Workflow Example

```bash
# 1. One-time setup
ssh yourusername@crux.alcf.anl.gov
cd ~
git clone https://github.com/AdvancedPhotonSource/GSAS-II.git
git clone <your-processor-repo>
cd Processor
bash scripts/crux_setup.sh  # Wait 10-15 min

# 2. Transfer data
# (do this from your local machine)
rsync -avz ~/xrd_data/ crux.alcf.anl.gov:~/xrd_data/

# 3. Submit job
# (back on Crux)
cd ~/Processor
nano scripts/submit_crux_production.pbs  # Edit project name
qsub scripts/submit_crux_production.pbs

# 4. Monitor
qstat -u $USER
tail -f ~/xrd_prod_*.out

# 5. Download results
# (from your local machine)
rsync -avz crux.alcf.anl.gov:~/xrd_data/Images/ ./results/
```

---

## Performance Tips

1. **Start small:** Test with debug queue (4 nodes) first
2. **Monitor efficiency:** Check worker utilization in job output
3. **Optimize chunks:** Adjust `spacing` parameter in submitted_values.json
4. **Use fast queue:** Debug queue has fastest turnaround for testing
5. **Batch processing:** Process multiple samples in one job

---

## Getting Help

- **ALCF Support**: [email protected]
- **System Status**: https://status.alcf.anl.gov
- **Full Documentation**: `docs/CRUX_DEPLOYMENT.md`
- **Check queue**: `qstat -a`
- **Check modules**: `module avail`

---

## Summary Commands

```bash
# Setup (one-time)
bash scripts/crux_setup.sh

# Activate environment
source ~/Processor/activate_xrd.sh

# Test
python -c "import G2script; from hpc_cluster import get_dask_client; print('Ready!')"

# Submit job
qsub scripts/submit_crux_debug.pbs  # or submit_crux_production.pbs

# Monitor
qstat -u $USER
tail -f ~/xrd_*.out

# Download results
rsync -avz crux.alcf.anl.gov:~/xrd_data/Images/ ./results/
```

---

**Version:** 1.4 - GSAS-II Compilation Support
**Last Updated:** January 2025
**Author:** William Gonzalez
