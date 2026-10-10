#!/usr/bin/env python3
"""Run the pinned official Hyperframes check/snapshot/render loop."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_VERSION = "0.7.65"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--snapshots", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--quality", choices=("draft", "standard", "high"), default="high")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_only and args.render:
        raise SystemExit("choose --check-only or --render, not both")
    if not args.check_only and not args.render:
        raise SystemExit("choose --check-only or --render")
    project = args.project.resolve()
    if not (project / "index.html").exists():
        raise SystemExit("project index.html missing")
    npx = shutil.which("npx")
    npm = shutil.which("npm")
    if not npx or not npm:
        raise SystemExit("Node.js 22+, npm, and npx are required")
    major = int(subprocess.check_output([shutil.which("node") or "node", "--version"], text=True).strip().lstrip("v").split(".")[0])
    if major < 22:
        raise SystemExit("Hyperframes requires Node.js 22+")
    if not (project / "node_modules" / "gsap" / "dist" / "gsap.min.js").exists():
        subprocess.run([npm, "install", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=project, check=True)
    version = os.environ.get("HYPERFRAMES_VERSION", DEFAULT_VERSION)
    base = [npx, "--yes", f"hyperframes@{version}"]
    command_env = os.environ.copy()
    if not shutil.which("ffprobe"):
        fallback_dir = Path(__file__).resolve().parent
        command_env["PATH"] = str(fallback_dir) + os.pathsep + command_env.get("PATH", "")
    check = base + ["check", str(project)]
    if args.snapshots:
        check.append("--snapshots")
    subprocess.run(check, cwd=project, env=command_env, check=True)
    if args.check_only:
        print("Hyperframes check passed; open preview for approval before final render")
        return 0
    output = args.output.resolve() if args.output else (project / "renders" / "final.mp4")
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(base + ["render", str(project), "--quality", args.quality, "--output", str(output)], cwd=project, env=command_env, check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise SystemExit("Hyperframes render did not create a non-empty output")
    print(f"Rendered with Hyperframes {version}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
