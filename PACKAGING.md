# Packaging Guide for File Duplicate Finder

This guide covers all packaging options for File Duplicate Finder, including PyPI, standalone executables, Docker containers, and platform-specific builds.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [PyPI Distribution](#pypi-distribution)
3. [Standalone Executables](#standalone-executables)
4. [Docker Containers](#docker-containers)
5. [Platform-Specific Builds](#platform-specific-builds)
6. [Automated Builds](#automated-builds)
7. [Installation Scripts](#installation-scripts)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before building packages, ensure you have the following installed:

### For All Builds
- Python 3.8 or higher
- pip and setuptools
- Git (for version control)

### For PyPI Distribution
```bash
pip install build twine
```

### For Standalone Executables
```bash
pip install pyinstaller
```

### For Docker
- Docker Engine
- Docker Compose (optional)

## PyPI Distribution

### Building PyPI Package

1. **Update version** in `pyproject.toml` and `version_info.txt`
2. **Build the package**:
   ```bash
   python build_tool.py pypi
   ```
   or manually:
   ```bash
   python -m build
   ```

3. **Test the package** (optional):
   ```bash
   twine check dist/*
   ```

4. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```

### Installing from PyPI

```bash
# Install CLI only
pip install filedupfinder

# Install with GUI support
pip install filedupfinder[gui]

# Install development dependencies
pip install filedupfinder[dev]
```

## Standalone Executables

### Building Standalone Executables

The build script automatically creates standalone executables for the current platform:

```bash
# Build for current platform
python build_tool.py standalone

# Build for specific platform
python build_tool.py standalone linux
python build_tool.py standalone windows
python build_tool.py standalone macos
```

### Manual PyInstaller Build

```bash
# CLI executable
pyinstaller --onefile --console --name filedupfinder src/filedupfinder/__main__.py

# GUI executable (requires PySide6)
pyinstaller --onefile --windowed --name filedupfinder-gui \
  --add-data "assets/fdf-icon.ico:assets/" \
  src/gui/gui_app.py
```

### Platform-Specific Considerations

#### Linux
- Executables are built as ELF binaries
- May require additional libraries on older distributions
- Consider using AppImage for better distribution

#### Windows
- Creates `.exe` files
- May trigger antivirus warnings (false positive)
- Consider code signing for production releases

#### macOS
- Creates universal binaries (Intel + Apple Silicon)
- May require notarization for distribution
- Consider using DMG for distribution

## Docker Containers

### Building Docker Image

```bash
# Build using build script
python build_tool.py docker

# Manual build
docker build -t filedupfinder:latest .
```

### Running with Docker

```bash
# Basic usage
docker run -v $(pwd):/app/data filedupfinder:latest /app/data

# With custom arguments
docker run -v $(pwd):/app/data filedupfinder:latest /app/data --threads 4

# Interactive mode
docker run -it -v $(pwd):/app/data filedupfinder:latest /app/data --interactive
```

### Using Docker Compose

```bash
# Start the service
docker-compose up

# Run with custom command
docker-compose run filedupfinder /app/data --demo
```

### Docker Image Optimization

The Dockerfile is optimized for:
- **Small size**: Uses Python slim image
- **Security**: Runs as non-root user
- **Caching**: Copies requirements first
- **Multi-stage builds**: Can be extended for smaller final image

## Platform-Specific Builds

### Linux Builds

#### Ubuntu/Debian
```bash
# Install dependencies
sudo apt-get update
sudo apt-get install python3-dev python3-pip

# Build
python build_tool.py standalone linux
```

#### CentOS/RHEL
```bash
# Install dependencies
sudo yum install python3-devel python3-pip

# Build
python build_tool.py standalone linux
```

### Windows Builds

#### Using WSL (Recommended)
```bash
# Install WSL and Ubuntu
wsl --install

# Follow Linux build instructions
```

#### Native Windows
```bash
# Install Python and dependencies
# Use the build script
python build_tool.py standalone windows
```

### macOS Builds

```bash
# Install dependencies
brew install python3

# Build
python build_tool.py standalone macos
```

## Automated Builds

### GitHub Actions

The project includes GitHub Actions workflows that automatically:

1. **Test** on multiple Python versions
2. **Build** PyPI packages
3. **Create** standalone executables for all platforms
4. **Build** Docker images
5. **Release** when tags are pushed

### Setting Up GitHub Secrets

For automated releases, set these secrets in your GitHub repository:

- `PYPI_API_TOKEN`: Your PyPI API token
- `DOCKER_USERNAME`: Your Docker Hub username

### Manual Release Process

1. **Update version**:
   ```bash
   # Update pyproject.toml
   # Update version_info.txt
   # Update CHANGELOG.md
   ```

2. **Commit and tag**:
   ```bash
   git add .
   git commit -m "Release v0.7.0"
   git tag v0.7.0
   git push origin main --tags
   ```

3. **Monitor builds** on GitHub Actions

## Installation Scripts

The build script creates platform-specific installation scripts:

### Linux
```bash
chmod +x scripts/install-linux.sh
./scripts/install-linux.sh
```

### Windows
```cmd
scripts\install-windows.bat
```

### macOS
```bash
chmod +x scripts/install-macos.sh
./scripts/install-macos.sh
```

## Distribution Formats

### PyPI Package
- **Format**: Wheel and source distribution
- **Installation**: `pip install filedupfinder`
- **Best for**: Python developers, easy updates

### Standalone Executables
- **Format**: Single executable file
- **Installation**: Download and run
- **Best for**: End users, no Python required

### Docker Image
- **Format**: Container image
- **Installation**: `docker pull filedupfinder`
- **Best for**: Server environments, consistent execution

### AppImage (Linux)
```bash
# Create AppImage (requires appimagetool)
appimagetool dist/standalone-linux/ filedupfinder.AppImage
```

### DMG (macOS)
```bash
# Create DMG (requires create-dmg)
create-dmg \
  --volname "File Duplicate Finder" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "filedupfinder" 200 190 \
  --hide-extension "filedupfinder" \
  --app-drop-link 600 185 \
  "FileDuplicateFinder.dmg" \
  "dist/standalone-macos/"
```

## Troubleshooting

### Common Issues

#### PyInstaller Issues
```bash
# Missing modules
pyinstaller --hidden-import=module_name

# Missing data files
pyinstaller --add-data "path/to/file:destination"

# Debug build
pyinstaller --debug all
```

#### Docker Issues
```bash
# Build context too large
# Check .dockerignore file

# Permission issues
docker run --user $(id -u):$(id -g) filedupfinder:latest

# Volume mounting issues
docker run -v /host/path:/container/path filedupfinder:latest
```

#### Cross-Platform Builds
```bash
# Use Docker for cross-platform builds
docker run --rm -v $(pwd):/src -w /src cdrx/pyinstaller-linux:python3

# Or use GitHub Actions for automated builds
```

### Performance Optimization

#### Executable Size
```bash
# Exclude unnecessary modules
pyinstaller --exclude-module=matplotlib --exclude-module=numpy

# Use UPX compression
pyinstaller --upx-dir=/path/to/upx
```

#### Docker Image Size
```bash
# Use multi-stage builds
# Use Alpine Linux base
# Remove unnecessary files
```

## Best Practices

1. **Version Management**: Always update version in all files
2. **Testing**: Test packages before distribution
3. **Documentation**: Keep installation instructions updated
4. **Security**: Sign executables when possible
5. **Monitoring**: Monitor download statistics and user feedback

## Support

For packaging issues:
1. Check the troubleshooting section
2. Review GitHub Actions logs
3. Create an issue with detailed error information
4. Include system information and build logs 