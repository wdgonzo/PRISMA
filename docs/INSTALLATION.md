# PRISMA Installation Guide

Complete installation instructions for PRISMA - Parallel Refinement and Integration System for Multi-Azimuthal Analysis.

---

## Table of Contents
- [System Requirements](#system-requirements)
- [Windows Installation (Recommended)](#windows-installation-recommended)
- [Manual Installation](#manual-installation)
- [GSAS-II Configuration](#gsas-ii-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

---

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 version 1809 (October 2018 Update) or later
- **Processor**: Intel Core i5 or equivalent (64-bit)
- **RAM**: 4GB minimum
- **Disk Space**: 2GB for PRISMA + ~500MB for GSAS-II
- **Display**: 1280x720 minimum resolution

### Recommended Requirements
- **Operating System**: Windows 10/11 (latest updates)
- **Processor**: Intel Core i7 or AMD Ryzen 7 (multi-core)
- **RAM**: 16GB or more
- **Disk Space**: 10GB+ for data processing
- **Display**: 1920x1080 or higher

### Additional Software
- **Git**: Required for automatic GSAS-II download
  - Download from: https://git-scm.com/download/win
  - Optional if providing existing GSAS-II installation

---

## Windows Installation (Recommended)

### Step 1: Download Installer

1. Go to the [PRISMA Releases page](https://github.com/wdgonzo/PRISMA/releases/latest)
2. Download **`PRISMA-Installer-v0.3.0-beta.exe`** (latest version)
3. Optionally download the SHA256 checksum file for verification

### Step 2: Verify Download (Optional but Recommended)

Open PowerShell and run:
```powershell
certutil -hashfile PRISMA-Installer-v0.3.0-beta.exe SHA256
```

Compare the output with the value in `PRISMA-Installer-v0.3.0-beta.exe.sha256`.

### Step 3: Run Installer

1. **Right-click** `PRISMA-Installer-v0.3.0-beta.exe`
2. Select **"Run as administrator"** (required)
3. If Windows SmartScreen appears, click **"More info"** then **"Run anyway"**

### Step 4: Follow Installation Wizard

#### Welcome Screen
Click **Next** to begin installation.

#### License Agreement
Read the license and click **I accept** if you agree.

#### Installation Directory
- Default: `C:\Program Files\PRISMA`
- Change if desired, then click **Next**

#### GSAS-II Setup (Important!)
Choose one of three options:

**Option 1: Automatic Download (Recommended)**
- Requires Git installed
- Downloads and configures GSAS-II automatically (~500MB)
- Takes 2-5 minutes depending on connection

**Option 2: Use Existing Installation**
- If you already have GSAS-II installed
- Browse to your GSAS-II directory
- Installer will validate the installation

**Option 3: Skip (Configure Later)**
- Install PRISMA only
- Configure GSAS-II manually after installation

#### Installation Progress
- Wait for files to be installed (1-2 minutes)
- GSAS-II download/configuration if selected

#### Completion
- Check **"Launch PRISMA"** to start immediately
- Click **Finish**

### Step 5: First Launch

When PRISMA launches for the first time:

1. **Workspace Setup Dialog** appears
   - Select a directory for your data (e.g., `Documents\PRISMA`)
   - PRISMA creates standard subdirectories:
     - `Images/` - Raw diffraction images
     - `Processed/` - Processed datasets
     - `Analysis/` - Analysis outputs
     - `recipes/` - Processing recipes

2. **Update Check** (if online)
   - PRISMA checks for updates automatically
   - Can be disabled in settings

---

## Manual Installation

For advanced users or non-standard setups.

### Prerequisites

1. **Python 3.10 or later**
   ```bash
   python --version  # Should show 3.10+
   ```

2. **Git** (for GSAS-II)
   ```bash
   git --version
   ```

### Installation Steps

1. **Clone PRISMA Repository**
   ```bash
   git clone https://github.com/wdgonzo/PRISMA.git
   cd PRISMA
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install GSAS-II**
   ```bash
   # Clone GSAS-II
   git clone https://github.com/AdvancedPhotonSource/GSAS-II.git

   # Configure GSAS-II for PRISMA
   python XRD/initialize_gsas_headless.py path/to/GSAS-II
   ```

4. **Verify Installation**
   ```bash
   python -m XRD.tools.verify_installation
   ```

5. **Launch PRISMA**
   ```bash
   python run_prisma.py
   ```

---

## GSAS-II Configuration

GSAS-II is required for XRD peak fitting in PRISMA.

### Automatic Configuration (Installer)

If you chose automatic GSAS-II download during installation, it's already configured!

### Manual Configuration

1. **From PRISMA GUI:**
   - Launch PRISMA
   - Go to: **File → Settings**
   - Under "GSAS-II Path", browse to your GSAS-II directory
   - Click **Save**

2. **From Command Line:**
   ```bash
   python XRD/initialize_gsas_headless.py C:\path\to\GSAS-II
   ```

3. **Environment Variables (Advanced):**
   ```batch
   SET GSAS2DIR=C:\path\to\GSAS-II
   SET PYTHONPATH=%GSAS2DIR%;%PYTHONPATH%
   ```

### Verifying GSAS-II Configuration

Run verification tool:
```bash
prisma --verify
```

Look for:
```
✓ PASS  GSAS-II (G2script)
         Using G2script shortcut
```

---

## Verification

### Post-Installation Check

After installation, verify everything works:

1. **Launch PRISMA**
   - Desktop shortcut: Double-click **PRISMA**
   - Start Menu: **PRISMA → PRISMA**
   - Command line: `prisma` or `python run_prisma.py`

2. **Run Verification Tool**
   ```bash
   prisma --verify
   ```

   Expected output:
   ```
   ✓ PASS  Python version (Python 3.11.x)
   ✓ PASS  Dependencies (All packages found)
   ✓ PASS  XRD modules (All modules importable)
   ✓ PASS  GSAS-II (GSAS-II accessible)
   ✓ PASS  Workspace (Configured and valid)
   ```

3. **Test Basic Functionality**
   - Open **Recipe Builder** tab
   - Open **Batch Processor** tab
   - Check **Tools → Check for Updates**

---

## Troubleshooting

### Installation Issues

#### "Windows protected your PC" SmartScreen Warning
**Solution:**
1. Click **"More info"**
2. Click **"Run anyway"**
3. This is normal for new applications

#### "Access Denied" During Installation
**Solution:**
- Right-click installer and select **"Run as administrator"**
- Installation requires admin rights for Program Files

#### Installer Fails with "PRISMA.exe not found"
**Solution:**
- Re-download installer (may be corrupted)
- Check antivirus hasn't quarantined files
- Verify checksum matches

### GSAS-II Issues

#### "GSAS-II not found" Error
**Solutions:**
1. **Reconfigure GSAS-II:**
   ```bash
   python XRD/initialize_gsas_headless.py C:\path\to\GSAS-II
   ```

2. **Check GSAS2DIR environment variable:**
   ```batch
   echo %GSAS2DIR%
   ```

3. **Reinstall GSAS-II:**
   ```bash
   git clone https://github.com/AdvancedPhotonSource/GSAS-II.git
   ```

#### "ImportError: No module named GSASII"
**Solution:**
- Ensure GSAS-II is in PYTHONPATH:
  ```batch
  SET PYTHONPATH=C:\path\to\GSAS-II;%PYTHONPATH%
  ```

### Runtime Issues

#### PRISMA Won't Launch
**Solutions:**
1. Check event logs: Windows Logs → Application
2. Run from command line to see errors:
   ```bash
   cd "C:\Program Files\PRISMA"
   PRISMA.exe
   ```

3. Reinstall PRISMA

#### "DLL Load Failed" Errors
**Solution:**
- Install Microsoft Visual C++ Redistributable:
  https://aka.ms/vs/17/release/vc_redist.x64.exe

#### Out of Memory Errors
**Solution:**
- Close other applications
- Increase system virtual memory
- Process smaller batches of images

### Update Issues

#### Update Check Fails
**Solutions:**
- Check internet connection
- Check firewall/proxy settings
- Disable update checks: Settings → Uncheck "Check for updates"

#### "Update Available" but Download Fails
**Solution:**
- Download manually from: https://github.com/wdgonzo/PRISMA/releases
- Antivirus may be blocking download

---

## Uninstallation

### Using Windows Uninstaller

1. **Open Windows Settings**
   - Press `Windows + I`

2. **Apps → Apps & features**

3. **Find "PRISMA"**
   - Click **Uninstall**
   - Click **Uninstall** again to confirm

4. **Follow Uninstaller Wizard**
   - Click **Next** through the wizard
   - Choose whether to keep user data

### Manual Uninstallation

If uninstaller is unavailable:

1. **Delete Installation Directory**
   ```batch
   rmdir /s "C:\Program Files\PRISMA"
   ```

2. **Delete User Data (Optional)**
   ```batch
   rmdir /s "%USERPROFILE%\.prisma"
   ```

3. **Delete Desktop Shortcut**
   ```batch
   del "%USERPROFILE%\Desktop\PRISMA.lnk"
   ```

4. **Delete Start Menu Entry**
   ```batch
   rmdir /s "%APPDATA%\Microsoft\Windows\Start Menu\Programs\PRISMA"
   ```

5. **Remove GSAS-II (Optional)**
   - Only if installed by PRISMA installer
   - Delete GSAS-II directory

---

## Getting Help

### Support Resources

- **Documentation**: https://github.com/wdgonzo/PRISMA/blob/main/README.md
- **Issue Tracker**: https://github.com/wdgonzo/PRISMA/issues
- **GSAS-II Help**: https://subversion.xray.aps.anl.gov/trac/pyGSAS

### Reporting Issues

When reporting issues, include:
1. PRISMA version (`prisma --version`)
2. Windows version
3. Error messages (full text)
4. Steps to reproduce
5. Screenshots if applicable

### Community

- GitHub Discussions (coming soon)
- Email: [Contact information to be added]

---

## Advanced Topics

### HPC Deployment

For HPC/supercomputer deployment, see:
- [docs/CRUX_DEPLOYMENT.md](CRUX_DEPLOYMENT.md) - ALCF Crux setup
- [docs/CRUX_QUICKSTART.md](CRUX_QUICKSTART.md) - Quick HPC guide

### Development Installation

For developers wanting to modify PRISMA:

```bash
git clone https://github.com/wdgonzo/PRISMA.git
cd PRISMA
pip install -e .  # Editable install
pip install -r installer/requirements_build.txt  # Build tools
```

See [docs/BUILDING.md](BUILDING.md) for building executables.

---

**Last Updated**: November 2025
**Version**: Beta 0.3
