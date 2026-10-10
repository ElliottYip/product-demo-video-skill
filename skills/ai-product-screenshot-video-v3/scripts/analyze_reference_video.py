#!/usr/bin/env python3
"""Extract metadata and evenly sampled frames from a style-reference video."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if not args.video.is_file():
        raise SystemExit(f"missing video: {args.video}")
    if args.samples < 2 or args.samples > 60:
        raise SystemExit("--samples must be between 2 and 60")
    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        raise SystemExit("ffmpeg and ffprobe are required")
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(run([
        ffprobe, "-v", "error", "-show_entries",
        "format=duration,format_name,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
        "-of", "json", str(args.video.resolve()),
    ]))
    duration = float(metadata["format"]["duration"])
    # Never seek to the exact EOF: many containers expose duration as the first
    # timestamp with no decodable frame.
    last_frame = max(0.0, duration - 0.08)
    timestamps = [last_frame * index / (args.samples - 1) for index in range(args.samples)]
    frames = []
    for index, timestamp in enumerate(timestamps):
        name = f"frame-{index + 1:03d}-{timestamp:07.3f}s.png"
        path = args.output / name
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}",
            "-i", str(args.video.resolve()), "-frames:v", "1", "-pix_fmt", "rgb24", "-y", str(path),
        ], check=True)
        frames.append({"timestamp": round(timestamp, 3), "file": name})
    payload = {
        "source": str(args.video.resolve()),
        "metadata": metadata,
        "sampled_frames": frames,
        "adaptation_rule": "Extract abstract pacing and hierarchy only; do not copy branding, watermark, music, or frame-for-frame composition."
    }
    (args.output / "reference-analysis.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {duration:.3f}s reference into {args.output} ({len(frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
