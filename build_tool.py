#!/usr/bin/env python3
"""
Build script for File Duplicate Finder
Supports building for PyPI, standalone executables, and Docker containers.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import List, Optional


class Builder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.src_dir = self.project_root / "src"
        
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> bool:
        """Run a command and return success status."""
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
            return False

    def run_command_with_env(self, cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None, capture_output: bool = False) -> bool:
        """Run a command with custom environment and return success status."""
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.project_root,
                check=True,
                capture_output=capture_output,
                text=True,
                env=env
            )
            if capture_output:
                print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {' '.join(cmd)}")
            if capture_output:
                print(f"Error: {e.stderr}")
            return False

    def clean_build_dirs(self):
        """Clean build and dist directories."""
        print("Cleaning build directories...")
        for dir_path in [self.dist_dir, self.build_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"Removed {dir_path}")

    def build_pypi_package(self):
        """Build PyPI package (wheel and source distribution)."""
        print("\n=== Building PyPI Package ===")
        
        # Clean previous builds
        self.clean_build_dirs()
        
        # Set environment variables to limit resource usage
        env = os.environ.copy()
        env['PYTHONHASHSEED'] = '0'  # Deterministic builds
        env['PYTHONDONTWRITEBYTECODE'] = '1'  # Don't write .pyc files
        env['PYTHONPATH'] = str(self.src_dir)  # Add src to Python path
        
        # Use build module with single worker
        build_cmd = [
            sys.executable, "-m", "build", 
            "--no-isolation"  # Use system packages when possible
        ]
        
        print("Building PyPI package...")
        if not self.run_command_with_env(build_cmd, env=env):
            print("Failed to build PyPI package")
            return False
            
        print("PyPI package built successfully!")
        return True

    def build_standalone_executable(self, platform_name: str):
        """Build standalone executable using PyInstaller."""
        print(f"\n=== Building Standalone Executable for {platform_name} ===")
        
        # Install PyInstaller if not available
        try:
            import PyInstaller
        except ImportError:
            print("Installing PyInstaller...")
            if not self.run_command([sys.executable, "-m", "pip", "install", "pyinstaller"]):
                print("Failed to install PyInstaller")
                return False

        # Create platform-specific build directory
        platform_build_dir = self.dist_dir / f"standalone-{platform_name}"
        platform_build_dir.mkdir(parents=True, exist_ok=True)

        # Build CLI executable
        cli_spec = [
            "pyinstaller",
            "--onefile",
            "--console",
            "--name", "filedupfinder",
            "--distpath", str(platform_build_dir),
            "--workpath", str(self.build_dir / "cli"),
            "--specpath", str(self.build_dir / "cli"),
            str(self.src_dir / "filedupfinder" / "__main__.py")
        ]
        
        if not self.run_command(cli_spec):
            print("Failed to build CLI executable")
            return False

        # Build GUI executable (if PySide6 is available)
        try:
            import PySide6
            gui_spec = [
                "pyinstaller",
                "--onefile",
                "--windowed",
                "--name", "filedupfinder-gui",
                "--distpath", str(platform_build_dir),
                "--workpath", str(self.build_dir / "gui"),
                "--specpath", str(self.build_dir / "gui"),
                "--add-data", f"{self.project_root}/assets/fdf-icon.ico{os.pathsep}assets/",
                str(self.src_dir / "gui" / "gui_app.py")
            ]
            
            if not self.run_command(gui_spec):
                print("Failed to build GUI executable")
                return False
                
        except ImportError:
            print("PySide6 not available, skipping GUI executable")

        print(f"Standalone executables built for {platform_name}!")
        return True

    def build_docker_image(self):
        """Build Docker image."""
        print("\n=== Building Docker Image ===")
        
        # Create Dockerfile if it doesn't exist
        dockerfile_path = self.project_root / "Dockerfile"
        if not dockerfile_path.exists():
            print("Creating Dockerfile...")
            self.create_dockerfile()
        
        # Build Docker image
        image_name = "filedupfinder:latest"
        if not self.run_command(["docker", "build", "-t", image_name, "."]):
            print("Failed to build Docker image")
            return False
            
        print("Docker image built successfully!")
        return True

    def create_dockerfile(self):
        """Create a Dockerfile for the application."""
        dockerfile_content = '''# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .
COPY LICENSE .

# Install the package in development mode
RUN pip install -e .

# Create a non-root user
RUN useradd -m -u 1000 filedupfinder
USER filedupfinder

# Set default command
ENTRYPOINT ["filedupfinder"]

# Default arguments (can be overridden)
CMD ["--help"]
'''
        
        with open(self.project_root / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        print("Dockerfile created!")

    def create_docker_compose(self):
        """Create docker-compose.yml for easy deployment."""
        compose_content = '''version: '3.8'

services:
  filedupfinder:
    build: .
    image: filedupfinder:latest
    container_name: filedupfinder
    volumes:
      - ./data:/app/data
      - ./output:/app/output
    environment:
      - PYTHONUNBUFFERED=1
    command: ["--help"]
'''
        
        with open(self.project_root / "docker-compose.yml", "w") as f:
            f.write(compose_content)
        print("docker-compose.yml created!")

    def create_install_scripts(self):
        """Create platform-specific install scripts."""
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Linux install script
        linux_install = '''#!/bin/bash
# Linux installation script for File Duplicate Finder

set -e

echo "Installing File Duplicate Finder..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3.8+ first."
    exit 1
fi

# Install the package
pip3 install --user .

echo "Installation complete!"
echo "Run 'filedupfinder --help' to get started"
echo "Run 'filedupfinder-gui' to start the GUI"
'''
        
        with open(scripts_dir / "install-linux.sh", "w") as f:
            f.write(linux_install)
        os.chmod(scripts_dir / "install-linux.sh", 0o755)
        
        # Windows install script
        windows_install = '''@echo off
REM Windows installation script for File Duplicate Finder

echo Installing File Duplicate Finder...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is required but not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Install the package
pip install --user .

echo Installation complete!
echo Run 'filedupfinder --help' to get started
echo Run 'filedupfinder-gui' to start the GUI
pause
'''
        
        with open(scripts_dir / "install-windows.bat", "w") as f:
            f.write(windows_install)
        
        # macOS install script
        macos_install = '''#!/bin/bash
# macOS installation script for File Duplicate Finder

set -e

echo "Installing File Duplicate Finder..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3.8+ first."
    exit 1
fi

# Install the package
pip3 install --user .

echo "Installation complete!"
echo "Run 'filedupfinder --help' to get started"
echo "Run 'filedupfinder-gui' to start the GUI"
'''
        
        with open(scripts_dir / "install-macos.sh", "w") as f:
            f.write(macos_install)
        os.chmod(scripts_dir / "install-macos.sh", 0o755)
        
        print("Install scripts created in scripts/ directory!")

    def test_package(self):
        """Test package configuration without building."""
        print("\n=== Testing Package Configuration ===")
        
        # Test if we can import the package
        try:
            sys.path.insert(0, str(self.src_dir))
            import filedupfinder
            print("✅ Package imports successfully")
            
            # Test CLI entry point
            from filedupfinder.__main__ import main
            print("✅ CLI entry point works")
            
            # Test GUI entry point (if available)
            try:
                from gui.gui_app import main as gui_main
                print("✅ GUI entry point works")
            except ImportError:
                print("⚠️  GUI entry point not available (PySide6 not installed)")
                
        except ImportError as e:
            print(f"❌ Package import failed: {e}")
            return False
            
        # Test pyproject.toml syntax
        try:
            import tomllib
            with open(self.project_root / "pyproject.toml", "rb") as f:
                tomllib.load(f)
            print("✅ pyproject.toml syntax is valid")
        except Exception as e:
            print(f"❌ pyproject.toml syntax error: {e}")
            return False
            
        print("✅ Package configuration test passed!")
        return True

    def build_all(self):
        """Build everything for all platforms."""
        print("=== File Duplicate Finder Build System ===")
        
        # Build PyPI package
        if not self.build_pypi_package():
            return False
        
        # Build standalone executables for current platform
        current_platform = platform.system().lower()
        if not self.build_standalone_executable(current_platform):
            return False
        
        # Create Docker files
        self.create_docker_compose()
        
        # Create install scripts
        self.create_install_scripts()
        
        print("\n=== Build Complete! ===")
        print(f"PyPI package: {self.dist_dir}")
        print(f"Standalone executable: {self.dist_dir}/standalone-{current_platform}")
        print("Docker files created")
        print("Install scripts created in scripts/")
        return True


def main():
    """Main entry point."""
    builder = Builder()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            success = builder.test_package()
        elif command == "pypi":
            success = builder.build_pypi_package()
        elif command == "standalone":
            platform_name = sys.argv[2] if len(sys.argv) > 2 else platform.system().lower()
            success = builder.build_standalone_executable(platform_name)
        elif command == "docker":
            success = builder.build_docker_image()
        elif command == "clean":
            builder.clean_build_dirs()
            success = True
        else:
            print("Usage: python build.py [test|pypi|standalone|docker|clean|all]")
            print("  test      - Test package configuration (lightweight)")
            print("  pypi      - Build PyPI package")
            print("  standalone - Build standalone executable")
            print("  docker    - Build Docker image")
            print("  clean     - Clean build directories")
            print("  all       - Build everything (default)")
            return
    else:
        # Default: build everything
        success = builder.build_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 