# Building PRISMA from Source

Guide for developers who want to build PRISMA executables and installer from source code.

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Building PRISMA.exe](#building-prismaexe)
- [Building PRISMA-Installer.exe](#building-prisma-installerexe)
- [Complete Release Build](#complete-release-build)
- [Build Artifacts](#build-artifacts)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Python 3.10 or later**
   ```bash
   python --version
   ```

2. **PyInstaller**
   ```bash
   pip install pyinstaller
   ```

3. **Pillow** (for icon generation)
   ```bash
   pip install Pillow
   ```

4. **Inno Setup 6.2+** (Windows only)
   - Download from: https://jrsoftware.org/isdl.php
   - Install to default location

5. **Git**
   ```bash
   git --version
   ```

### PRISMA Dependencies

Install all PRISMA dependencies:
```bash
pip install -r requirements.txt
pip install -r installer/requirements_build.txt
```

### Directory Structure

Ensure you're in the PRISMA root directory:
```
PRISMA/
├── XRD/
├── installer/
├── scripts/
├── run_prisma.py
└── requirements.txt
```

---

## Building PRISMA.exe

The main application executable.

### Quick Build

```bash
cd installer
python build_exe.py
```

### Clean Build

```bash
python build_exe.py --clean
```

### Build Process

1. **Checks Prerequisites**
   - Verifies PyInstaller is installed
   - Creates application icon if missing

2. **Runs PyInstaller**
   - Uses `PRISMA.spec` configuration
   - Bundles all Python dependencies
   - Creates standalone executable

3. **Output**
   - `dist/PRISMA.exe` (~50-100MB)
   - One-file mode (single executable)

### Manual Build (Advanced)

If you need to customize the build:

1. Edit `installer/PRISMA.spec` as needed
2. Run PyInstaller directly:
   ```bash
   pyinstaller installer/PRISMA.spec --clean
   ```

### Build Configuration

Key settings in `PRISMA.spec`:

```python
# One-file vs one-dir mode
# Current: One-file (single .exe)
# Alternative: Uncomment COLLECT block for one-dir

# Console mode
console=False  # Windowed (no console)
# console=True  # Show console for debugging

# UPX compression
upx=True  # Compress executable
# upx=False  # Faster build, larger file

# Hidden imports
# Add modules that PyInstaller misses
hiddenimports=[...]
```

---

## Building PRISMA-Installer.exe

The Windows installer that packages PRISMA.exe.

### Prerequisites

**PRISMA.exe must be built first!**
```bash
cd installer
python build_exe.py
```

Verify it exists:
```bash
dir ..\dist\PRISMA.exe
```

### Quick Build

```bash
cd installer
python build_installer.py
```

### Build Process

1. **Checks Prerequisites**
   - Verifies PRISMA.exe exists
   - Finds Inno Setup compiler
   - Creates LICENSE file if missing

2. **Runs Inno Setup**
   - Compiles `prisma_installer.iss`
   - Packages PRISMA.exe and setup scripts
   - Creates wizard-based installer

3. **Output**
   - `installer/Output/PRISMA-Installer-v0.3.0-beta.exe` (~150-200MB)
   - SHA256 checksum file

### Manual Build (Advanced)

Using Inno Setup directly:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\prisma_installer.iss
```

### Installer Configuration

Key settings in `prisma_installer.iss`:

```pascal
#define MyAppVersion "0.3.0-beta"  // Update for new versions

[Setup]
PrivilegesRequired=admin  // Require admin for installation
Compression=lzma2/max     // Maximum compression
SolidCompression=yes      // Faster installation

[Tasks]
// Desktop shortcut (checked by default)
Name: "desktopicon"; Flags: checked

[Code]
// Custom GSAS-II setup wizard
// See script for full details
```

---

## Complete Release Build

Build everything in one command (recommended for releases).

### Full Release Build

```bash
cd scripts
python build_release.py
```

### What It Does

1. **Builds PRISMA.exe**
   - Runs `build_exe.py --clean`
   - Validates output

2. **Builds Installer**
   - Runs `build_installer.py`
   - Generates checksum

3. **Creates Release Package**
   - Copies to `releases/v0.3.0-beta/`
   - Generates release notes
   - Lists all artifacts

### Build Options

```bash
# Build specific version
python build_release.py --version 0.4.0-beta

# Skip PRISMA.exe build (use existing)
python build_release.py --skip-exe

# Skip installer build
python build_release.py --skip-installer
```

### Output

```
releases/v0.3.0-beta/
├── PRISMA-Installer-v0.3.0-beta.exe      (~150-200 MB)
├── PRISMA-Installer-v0.3.0-beta.exe.sha256
└── RELEASE_NOTES.md
```

---

## Build Artifacts

### Directory Structure After Build

```
PRISMA/
├── build/                     # PyInstaller build cache
│   └── PRISMA/
├── dist/                      # Built executable
│   ├── PRISMA.exe            # Main application
│   └── README.txt
├── installer/
│   ├── Output/               # Installer output
│   │   ├── PRISMA-Installer-v0.3.0-beta.exe
│   │   └── PRISMA-Installer-v0.3.0-beta.exe.sha256
│   └── prisma_icon.ico       # Generated icon
└── releases/
    └── v0.3.0-beta/          # Release package
        ├── PRISMA-Installer-v0.3.0-beta.exe
        ├── PRISMA-Installer-v0.3.0-beta.exe.sha256
        └── RELEASE_NOTES.md
```

### Cleaning Build Artifacts

```bash
# Remove all build artifacts
rmdir /s build dist
rmdir /s installer\Output
rmdir /s releases

# PyInstaller cache cleanup
python -m PyInstaller --clean installer\PRISMA.spec
```

---

## Troubleshooting

### PRISMA.exe Build Issues

#### "PyInstaller not found"
```bash
pip install pyinstaller
```

#### "Module not found" during build
Add to `hiddenimports` in `PRISMA.spec`:
```python
hiddenimports=[
    ...,
    'your_missing_module',
]
```

#### "Failed to execute script" when running exe
- Test in console mode first:
  ```python
  # In PRISMA.spec
  console=True  # Enable console
  ```
- Run exe from command line to see errors

#### Exe is too large (>200MB)
- Disable UPX: `upx=False`
- Check `excludes` list in `PRISMA.spec`
- Remove unnecessary data files

### Installer Build Issues

#### "Inno Setup not found"
- Install from: https://jrsoftware.org/isdl.php
- Add to PATH or use default location

#### "PRISMA.exe not found"
Build PRISMA.exe first:
```bash
cd installer
python build_exe.py
```

#### "LICENSE file not found"
Build script creates placeholder automatically, or add your own:
```bash
echo "Your License Text" > LICENSE
```

#### Compilation errors in .iss script
Check Inno Setup syntax:
- Run ISCC with /Q flag for detailed errors
- Open `prisma_installer.iss` in Inno Setup IDE

### Runtime Issues

#### PRISMA.exe crashes on launch
1. Test Python version:
   ```bash
   python run_prisma.py
   ```

2. Check dependencies:
   ```bash
   python -m XRD.tools.verify_installation
   ```

3. Rebuild with console mode to see errors

#### "DLL not found" errors
- Missing Visual C++ Redistributable
- Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

#### Icons not showing
- Ensure `prisma_icon.ico` exists
- Regenerate:
  ```bash
  cd installer
  python create_icon.py
  ```

---

## Advanced Topics

### Custom Icons

Replace default icon with professional design:

1. Create `prisma_icon.ico` (256x256, 128x128, 64x64, 48x48, 32x32, 16x16)
2. Place in `installer/prisma_icon.ico`
3. Rebuild

### Version Resource (Windows)

Add version information to PRISMA.exe:

1. Create `version_info.txt`:
   ```python
   VSVersionInfo(
     ffi=FixedFileInfo(
       filevers=(0, 3, 0, 0),
       prodvers=(0, 3, 0, 0),
       ...
     ),
     ...
   )
   ```

2. Update `PRISMA.spec`:
   ```python
   exe = EXE(
       ...,
       version='version_info.txt',
       ...
   )
   ```

### Code Signing (Optional)

For production releases, sign executables:

1. Obtain code signing certificate
2. Sign PRISMA.exe:
   ```bash
   signtool sign /f certificate.pfx /p password PRISMA.exe
   ```

3. Sign installer:
   ```bash
   signtool sign /f certificate.pfx /p password PRISMA-Installer.exe
   ```

### Cross-Platform Builds

**Note**: PRISMA currently targets Windows only.

For Linux support (future):
- Modify `PRISMA.spec` for Linux
- Use different installer (AppImage, deb, rpm)
- Test on target platforms

---

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Build PRISMA

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r installer/requirements_build.txt

      - name: Build release
        run: python scripts/build_release.py

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: PRISMA-Installer
          path: releases/*/PRISMA-Installer-*.exe
```

---

## Build Checklist

Before releasing a new version:

- [ ] Update version in `XRD/__init__.py`
- [ ] Update `CHANGELOG.md` with changes
- [ ] Update version in `installer/prisma_installer.iss`
- [ ] Clean previous builds
- [ ] Run full release build
- [ ] Test PRISMA.exe manually
- [ ] Test installer on clean Windows VM
- [ ] Verify all functionality works
- [ ] Generate checksums
- [ ] Create GitHub release
- [ ] Upload installer and checksum
- [ ] Update documentation

---

## Getting Help

### Build Issues

- Check this guide first
- Search [GitHub Issues](https://github.com/wdgonzo/PRISMA/issues)
- Create new issue with build logs

### Contributing

- Fork repository
- Create feature branch
- Make changes and test builds
- Submit pull request

---

**Last Updated**: November 2025
**Version**: Beta 0.3
