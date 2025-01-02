#!/usr/bin/env python3
import subprocess
import sys


def run_tests():
    result = subprocess.run(["pytest", "tests/"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    run_tests()
