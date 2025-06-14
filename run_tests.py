#!/usr/bin/env python3
"""
Test runner script with different test configurations.
Usage: python run_tests.py [options]
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return success status."""
    if description:
        print(f"\n🔥 {description}")
        print("=" * 50)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"✅ {description or 'Command'} passed!")
    else:
        print(f"❌ {description or 'Command'} failed!")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run tests with different configurations")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--auth", action="store_true", help="Run only auth tests")
    parser.add_argument("--songs", action="store_true", help="Run only song tests")
    parser.add_argument("--playlists", action="store_true", help="Run only playlist tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--parallel", "-n", type=int, help="Run tests in parallel (requires pytest-xdist)")

    args = parser.parse_args()

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.extend(["-v", "-s"])

    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])

    # Add marker filters
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.auth:
        markers.append("auth")
    if args.songs:
        markers.append("songs")
    if args.playlists:
        markers.append("playlists")

    if markers:
        cmd.extend(["-m", " or ".join(markers)])

    # Skip slow tests if requested
    if args.fast:
        cmd.extend(["-m", "not slow"])

    # Add test directory
    cmd.append("tests/")

    # Run the tests
    success = run_command(cmd, "Running tests")

    if args.coverage and success:
        print("\n📊 Coverage report generated in htmlcov/index.html")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()