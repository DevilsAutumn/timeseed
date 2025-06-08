#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run TimeSeed tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage reporting")
    parser.add_argument(
        "--parallel", "-j", type=int, default=1, help="Run tests in parallel (number of workers)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--markers", action="store_true", help="Show available test markers")

    args = parser.parse_args()

    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    base_cmd = ["python", "-m", "pytest"]

    if args.markers:
        subprocess.run(base_cmd + ["--markers"], check=True)
        return

    cmd_parts = base_cmd.copy()

    if args.parallel > 1:
        cmd_parts.extend(["-n", str(args.parallel)])

    if args.coverage:
        cmd_parts.extend(
            ["--cov=timeseed", "--cov-report=html", "--cov-report=term-missing", "--cov-report=xml"]
        )

    if args.verbose:
        cmd_parts.append("-vv")

    cmd_parts.append("tests/")

    cmd = " ".join(cmd_parts)

    print("🚀 Starting TimeSeed Test Suite")
    print(f"Command: {cmd}")

    success = run_command(cmd, "Running Tests")

    if success:
        print("\n🎉 All tests passed!")

        if args.coverage:
            print("\n📊 Coverage report generated:")
            print("  - HTML: htmlcov/index.html")
            print("  - XML: coverage.xml")
            print("  - Terminal output above")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


def run_test_categories():
    # TODO: Add more test categoreis : cli, performance, config, integration
    categories = [("Generator Tests", "python -m pytest tests/test_generator.py -v")]

    passed = 0
    failed = 0

    for name, cmd in categories:
        if run_command(cmd, name):
            passed += 1
        else:
            failed += 1

    print("\n📊 Test Summary:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📈 Success Rate: {passed / (passed + failed) * 100:.1f}%")

    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--comprehensive":
        success = run_test_categories()
        sys.exit(0 if success else 1)
    else:
        main()
