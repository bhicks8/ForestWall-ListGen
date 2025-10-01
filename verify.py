#!/usr/bin/env python3

# Verifies that changes to generated list files are within acceptable limits.
# Specifically, it checks that the number of lines in each list file has not changed
# by more than ±10% compared to the previous version in the git repository.
# Usage: python verify.py
# Intended for use as part of GitHub Actions workflow, but can be run manually as well

import glob
import subprocess
import sys

def old_line_count(path: str) -> int:
    try:
        data = subprocess.check_output(
            ["git", "show", f"HEAD:{path}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return len(data.splitlines())
    except subprocess.CalledProcessError:
        return 0

def percent_change(old: int, new: int) -> float:
    if old == 0:
        return 100.0 if new else 0.0
    return ((new - old) / old) * 100.0

def main(threshold: float) -> int:
    violations = []
    for path in sorted(glob.glob("lists/*.txt")):
        new_lines = sum(1 for _ in open(path, encoding="utf-8"))
        old_lines = old_line_count(path)
        if old_lines == 0:
            print(f"{path}: {new_lines} lines (new file)")
            continue  # New file, skip check
        pct = percent_change(old_lines, new_lines)
        if abs(pct) > threshold:
            violations.append((path, old_lines, new_lines, pct))

    if violations:
        for path, old_lines, new_lines, pct in violations:
            print(
                f"{path}: {old_lines} → {new_lines} lines "
                f"({pct:+.2f}% change) exceeds ±{threshold:.1f}% threshold"
            )
        return 1

    print(f"All list changes within ±{threshold:.1f}%.")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: python verify.py <threshold_percent>")
        sys.exit(1)
    else:
        try:
            threshold = float(sys.argv[1])
            sys.exit(main(threshold))
        except ValueError:
            print("Invalid threshold percentage.")
            print("Usage: python verify.py <threshold_percent>")
            sys.exit(1)