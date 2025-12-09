#!/usr/bin/env python3

# Goal: Configure git repo to use gitleaks & pre-commit to detect secrets while committing code.
# Author: Chinmay Jog
# Date: 9-Sep-2025

from pathlib import Path
import subprocess
import argparse
import shutil
from datetime import datetime
import sys

parser = argparse.ArgumentParser(
    description="Configure gitleaks & pre-commit on the current repo for secret scanning.")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--setup", action="store_true",
                   help="Set up the repository to detect secrets using gitleaks via pre-commit.")
group.add_argument("--dry-run", action="store_true",
                   help="Simulate setup actions without making any changes.")
args = parser.parse_args()


def check_in_repo():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        repo_toplevel = proc.stdout.strip()
    except subprocess.CalledProcessError:
        return False

    return Path.cwd().resolve() == Path(repo_toplevel).resolve()


def check_commands():
    gitleaks_version = ""
    gitleaks_status = False
    pre_commit_version = ""
    pre_commit_status = False

    if shutil.which("gitleaks") is None:
        return {
            "gitleaks": {"status": False, "version": ""},
            "pre-commit": {"status": False, "version": ""}
        }
    else:
        try:
            gitleaks = subprocess.run(
                ["gitleaks", "version"], capture_output=True, text=True, check=True)
            gitleaks_status = True
            gitleaks_version = gitleaks.stdout.strip().split()[
                0].removeprefix("v")
        except subprocess.CalledProcessError:
            gitleaks_status = False

    if shutil.which("pre-commit") is None:
        return {
            "gitleaks": {"status": False, "version": ""},
            "pre-commit": {"status": False, "version": ""}
        }
    else:
        try:
            pre_commit = subprocess.run(
                ["pre-commit", "--version"], capture_output=True, text=True, check=True)
            pre_commit_status = True
            pre_commit_version = pre_commit.stdout.strip().split(" ")[
                1]
        except subprocess.CalledProcessError:
            pre_commit_status = False

    return {
        "gitleaks": {
            "status": gitleaks_status,
            "version": gitleaks_version},
        "pre-commit": {
            "status": pre_commit_status,
            "version": pre_commit_version
        }
    }


def config_secscan(gitleaks_version, dry_run=False):
    pre_commit_config = f"""\
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v{gitleaks_version}
    hooks:
      - id: gitleaks
"""
    p = Path.cwd() / ".pre-commit-config.yaml"
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    backup_path = p.parent / f".pre-commit-config.yaml-{timestamp}"

    if dry_run:
        if p.exists():
            config_content = p.read_text()
            if f"id: gitleaks" in config_content:
                print("[dry-run] gitleaks already configured.")
                print("[dry-run] Would run: pre-commit install")
            else:
                print(f"[dry-run] Would move existing {p} -> {backup_path}")
                print(
                    f"[dry-run] Would write new {p} with content:\n{pre_commit_config}")
        else:
            print(
                f"[dry-run] Would write new {p} with content:\n{pre_commit_config}")

        print("[dry-run] Would run: pre-commit install")
        return

    if p.exists():
        config_content = p.read_text()
        if f"id: gitleaks" in config_content:
            print(
                f"Repository already configured with gitleaks rev {gitleaks_version}; only installing hooks.")
            subprocess.run(["pre-commit", "install"], check=True)
            print("pre-commit hooks installed")
            return
        shutil.move(str(p), str(backup_path))
        print(f"Existing config moved to {backup_path}")

    p.write_text(pre_commit_config)
    print(f"Wrote {p}")
    subprocess.run(["pre-commit", "install"], check=True)
    print(f"""
✅ Setup complete!

- Gitleaks version: {gitleaks_version}
- pre-commit version: {pre_commit_version}
- Config file: .pre-commit-config.yaml

Commits in this repo will now be scanned for secrets automatically.
""")


if __name__ == "__main__":
    if not check_in_repo():
        print(
            "❌ Not at a Git repository top-level. Run this script from the repository root.")
        sys.exit(1)

    commands_status = check_commands()
    gitleaks_status = commands_status["gitleaks"]["status"]
    gitleaks_version = commands_status["gitleaks"]["version"]
    pre_commit_status = commands_status["pre-commit"]["status"]
    pre_commit_version = commands_status["pre-commit"]["version"]
    status = gitleaks_status and pre_commit_status

    if not status:
        print("⚠️ Missing required tools or versions could not be determined.\n")
        print("➡️ Install gitleaks via: brew install gitleaks\n    More info: https://github.com/gitleaks/gitleaks")
        print("➡️ Install pre-commit via: brew install pre-commit\n    More info: https://pre-commit.com/")
        sys.exit(1)

    if args.dry_run:
        config_secscan(gitleaks_version, dry_run=True)
        sys.exit(0)

    if args.setup:
        config_secscan(gitleaks_version, dry_run=False)
        sys.exit(0)
