#!/usr/bin/env python3

# Verifies that changes to generated list files are within acceptable limits.
# Specifically, it checks that the number of lines in each list file has not changed
# by more than ±10% compared to the previous version published in the R2 bucket.
# Intended for use as part of GitHub Actions workflow, but can be run manually as well.
#
# Environment variables required for R2 comparison:
#   AWS_ACCESS_KEY_ID: R2 access key ID
#   AWS_SECRET_ACCESS_KEY: R2 secret access key
#   R2_ACCOUNT_ID: Cloudflare account ID
#   R2_BUCKET_NAME: Name of the R2 bucket

import glob
import os
import subprocess
import sys
import tempfile

cli_help = """
Usage: python verify.py <path_to_lists> <threshold_percent> <allow_deletions>
  path_to_lists: Directory containing the generated list files (e.g., 'lists')
  threshold_percent: Maximum allowed percentage change in line count (e.g., 10.0)
  allow_deletions: 'true' to allow file deletions, 'false' to disallow

Environment variables (required for R2 comparison):
  AWS_ACCESS_KEY_ID: R2 access key ID
  AWS_SECRET_ACCESS_KEY: R2 secret access key
  R2_ACCOUNT_ID: Cloudflare account ID
  R2_BUCKET_NAME: Name of the R2 bucket

If R2 environment variables are not set, all files are treated as new.
"""


def get_r2_config():
    """Get R2 configuration from environment variables."""
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    account_id = os.environ.get("R2_ACCOUNT_ID")
    bucket_name = os.environ.get("R2_BUCKET_NAME")
    
    if all([access_key, secret_key, account_id, bucket_name]):
        return {
            "endpoint_url": f"https://{account_id}.r2.cloudflarestorage.com",
            "bucket_name": bucket_name,
        }
    return None


def download_r2_files(r2_config, local_base_path: str, temp_dir: str) -> set:
    """
    Download files from R2 bucket to a temporary directory for comparison.
    Returns the set of downloaded file paths (relative to temp_dir).
    """
    endpoint_url = r2_config["endpoint_url"]
    bucket_name = r2_config["bucket_name"]
    
    # Use the same path structure as local (e.g., lists/)
    r2_prefix = f"s3://{bucket_name}/{local_base_path}/"
    
    try:
        # Sync R2 files to temp directory
        subprocess.run(
            [
                "aws", "s3", "sync",
                r2_prefix,
                os.path.join(temp_dir, local_base_path) + "/",
                "--endpoint-url", endpoint_url,
                "--only-show-errors",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        
        # Get list of downloaded files
        downloaded = []
        sync_path = os.path.join(temp_dir, local_base_path)
        if os.path.exists(sync_path):
            for f in os.listdir(sync_path):
                if f.endswith((".txt", ".rpz")):
                    downloaded.append(os.path.join(local_base_path, f))
        
        return set(downloaded)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to download from R2: {e.stderr}")
        return set()
    except FileNotFoundError:
        print("Warning: AWS CLI not found. Treating all files as new.")
        return set()


def normalize_paths(paths, start: str):
    return [os.path.normpath(os.path.relpath(p, start)) for p in paths]


def old_line_count_from_r2(path: str, temp_dir: str) -> int:
    """Get line count from the R2 version of a file (stored in temp_dir)."""
    r2_file = os.path.join(temp_dir, path)
    if os.path.exists(r2_file):
        with open(r2_file, encoding="utf-8") as f:
            return sum(1 for _ in f)
    return 0


def percent_change(old: int, new: int) -> float:
    if old == 0:
        return 100.0 if new else 0.0
    return ((new - old) / old) * 100.0


def passes_delete_check(current_files: set, r2_files: set, allowed: bool) -> bool:
    """Check if any files in R2 are missing from current files."""
    deleted_files = r2_files - current_files
    if deleted_files:
        for f in sorted(deleted_files):
            print(f"{f}: Deleted")
        if not allowed:
            print("File deletions are not allowed.")
            return False
        print("File deletions are allowed.")
    
    return True


def main(base_path: str, threshold: float, allow_delete: bool) -> int:
    # Get list of current local files (both .txt and .rpz)
    local_txt = glob.glob(base_path + "/*.txt")
    local_rpz = glob.glob(base_path + "/*.rpz")
    files = sorted(normalize_paths(local_txt + local_rpz, "."))
    current_files = set(files)
    
    # Get R2 configuration
    r2_config = get_r2_config()
    
    if r2_config:
        print(f"Comparing against R2 bucket: {r2_config['bucket_name']}")
        
        # Create temp directory for R2 files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download current R2 files
            r2_files = download_r2_files(r2_config, base_path, temp_dir)
            
            if not r2_files:
                print("No files found in R2 bucket. Treating all files as new.")
            
            # Check for deletions
            if not passes_delete_check(current_files, r2_files, allow_delete):
                return 1
            
            # Compare line counts
            violations = []
            checked_count = 0
            for path in files:
                with open(path, encoding="utf-8") as f:
                    new_lines = sum(1 for _ in f)
                old_lines = old_line_count_from_r2(path, temp_dir)
                
                if old_lines == 0:
                    print(f"{path}: {new_lines} lines (new file)")
                    continue  # New file, skip check
                
                pct = percent_change(old_lines, new_lines)
                if abs(pct) > threshold:
                    violations.append((path, old_lines, new_lines, pct))
                else:
                    checked_count += 1
                    print(f"{path}: {old_lines} → {new_lines} lines ({pct:+.2f}% change) - OK")
            
            if violations:
                print(f"\nFound {len(violations)} file(s) exceeding ±{threshold:.1f}% threshold:")
                for path, old_lines, new_lines, pct in violations:
                    print(
                        f"  {path}: {old_lines} → {new_lines} lines "
                        f"({pct:+.2f}% change)"
                    )
                return 1
            
            print(f"\nAll {checked_count} list changes within ±{threshold:.1f}%.")
            return 0
    else:
        print("R2 environment variables not configured. Treating all files as new.")
        for path in files:
            with open(path, encoding="utf-8") as f:
                new_lines = sum(1 for _ in f)
            print(f"{path}: {new_lines} lines (new file)")
        print(f"\nProcessed {len(files)} new file(s).")
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