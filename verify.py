#!/usr/bin/env python3

# Verifies that changes to generated list files are within acceptable limits.
# Specifically, it checks that the number of lines in each list file has not changed
# by more than ±10% compared to the previous version in the git repository.
# Intended for use as part of GitHub Actions workflow, but can be run manually as well.

import glob
import os
import subprocess
import sys

cli_help = """
Usage: python verify.py <path_to_lists> <threshold_percent> <allow_deletions>
  path_to_lists: Directory containing the generated list files (e.g., 'lists')
  threshold_percent: Maximum allowed percentage change in line count (e.g., 10.0)
  allow_deletions: 'true' to allow file deletions, 'false' to disallow
"""

def normalize_paths(paths: str, start: str) -> str:
    return [os.path.normpath(os.path.relpath(p, start)) for p in paths]

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

def tracked_lists_in_head(path: str):
    output = subprocess.check_output(
        ["git", "ls-tree", "--name-only", "HEAD", path + "/"],
        text=True,
    )
    return {line.strip() for line in output.splitlines() if line.strip().endswith(".txt")}

def passes_delete_check(base_path, files, allowed: bool) -> bool:
    head_files = set(normalize_paths(tracked_lists_in_head(base_path), "."))
    # Normalize the current files; Strictly speaking this should not be necessary
    # since glob.glob should return normalized paths, but just in case.
    current_files = set(normalize_paths(files, "."))

    for f in head_files - current_files:
        print(f"{f}: Deleted")
        if not allowed:
            print("File deletions are not allowed.")
            return False
    if (allowed):
        print("File deletions are allowed.")
    
    return True

def main(base_path: str, threshold: float, allow_delete: bool) -> int:
    files = sorted(normalize_paths(glob.glob(base_path + "/*.txt"), "."))

    if not passes_delete_check(base_path, files, allow_delete):
        return 1

    violations = []
    for path in files:
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
    if len(sys.argv) != 4:
        print(cli_help)
        sys.exit(1)
    else:
        try:
            base_path = sys.argv[1]
            threshold = float(sys.argv[2])

            allow_delete = sys.argv[3].lower()
            if allow_delete not in ("true", "false"):
                raise ValueError("Expected true or false for allow_deletions")
            allow_delete = allow_delete == "true"

            sys.exit(main(base_path, threshold, allow_delete))
        except ValueError:
            print("Invalid threshold percentage.")
            print(cli_help)
            sys.exit(1)