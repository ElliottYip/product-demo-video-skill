#!/usr/bin/env python3
"""Align sentence scenes to finished narration audio and emit matching text/SRT timing."""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    ffprobe = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required; set FFPROBE_BIN")
    value = subprocess.check_output([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nk=1:nw=1", str(path),
    ], text=True)
    return float(value.strip())


def align_scenes(scenes: list[dict], audio_duration: float, boundary_times: list[float] | None = None) -> list[dict]:
    """Apply reviewed sentence boundaries, or produce an explicitly draft allocation."""
    if not scenes:
        raise ValueError("storyboard must contain at least one sentence scene")
    if audio_duration <= 0:
        raise ValueError("audio duration must be positive")
    if boundary_times is not None:
        if len(boundary_times) != len(scenes) - 1:
            raise ValueError(f"expected {len(scenes) - 1} internal boundary times, got {len(boundary_times)}")
        ends = [round(float(value), 3) for value in boundary_times] + [round(audio_duration, 3)]
        if any(end <= start for start, end in zip([0.0] + ends[:-1], ends)) or ends[-1] > round(audio_duration, 3):
            raise ValueError("reviewed boundaries must be strictly increasing and inside the audio")
        fixed = [float(scene["fixed_duration"]) if scene.get("fixed_duration") is not None else None for scene in scenes]
        for index, fixed_value in enumerate(fixed):
            if fixed_value is not None:
                start = 0.0 if index == 0 else ends[index - 1]
                if abs((ends[index] - start) - fixed_value) > 0.015:
                    raise ValueError(f"reviewed boundaries violate fixed_duration for scene {index + 1}")
        aligned = []
        previous_end = 0.0
        for index, (scene, end) in enumerate(zip(scenes, ends)):
            item = copy.deepcopy(scene)
            item["start"] = previous_end
            item["end"] = end
            item["duration"] = round(end - previous_end, 3)
            item["subtitle"] = str(item.get("subtitle") or item.get("narration") or "").strip()
            if not str(item.get("narration") or "").strip():
                raise ValueError(f"scene {item.get('id', index + 1)} has empty narration")
            aligned.append(item)
            previous_end = end
        return aligned

    weights = [max(0.001, float(scene.get("duration") or 0)) for scene in scenes]
    fixed = [float(scene["fixed_duration"]) if scene.get("fixed_duration") is not None else None for scene in scenes]
    fixed_total = sum(value for value in fixed if value is not None)
    if fixed_total >= audio_duration:
        raise ValueError("fixed scene durations leave no room for the main narration")
    flexible_weight = sum(weight for weight, fixed_value in zip(weights, fixed) if fixed_value is None)
    if flexible_weight <= 0:
        raise ValueError("at least one non-fixed narration scene is required")
    flexible_duration = audio_duration - fixed_total
    target_durations = [
        fixed_value if fixed_value is not None else flexible_duration * scene_weight / flexible_weight
        for scene_weight, fixed_value in zip(weights, fixed)
    ]
    aligned = []
    cumulative = 0.0
    previous_end = 0.0
    for index, (scene, target_duration) in enumerate(zip(scenes, target_durations)):
        cumulative += target_duration
        end = round(audio_duration if index == len(scenes) - 1 else cumulative, 3)
        if end <= previous_end:
            raise ValueError("audio is too short to assign a positive millisecond range to every sentence")
        item = copy.deepcopy(scene)
        item["start"] = previous_end
        item["end"] = end
        item["duration"] = round(end - previous_end, 3)
        item["subtitle"] = str(item.get("subtitle") or item.get("narration") or "").strip()
        if not str(item.get("narration") or "").strip():
            raise ValueError(f"scene {item.get('id', index + 1)} has empty narration")
        aligned.append(item)
        previous_end = end
    return aligned


def clock(seconds: float, decimal: str = ".") -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}{decimal}{milliseconds:03d}"


def short_clock(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def timed_narration(scenes: list[dict]) -> str:
    rows = []
    for scene in scenes:
        rows.append(
            f"[{short_clock(float(scene['start']))} --> {short_clock(float(scene['end']))} | "
            f"{float(scene['duration']):.3f}秒] {str(scene['narration']).strip()}"
        )
    return "\n".join(rows) + "\n"


def srt_text(scenes: list[dict]) -> str:
    blocks = []
    for index, scene in enumerate(scenes, start=1):
        blocks.append(
            f"{index}\n{clock(float(scene['start']), ',')} --> {clock(float(scene['end']), ',')}\n"
            f"{str(scene.get('subtitle') or scene['narration']).strip()}"
        )
    return "\n\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output-storyboard", type=Path, help="Defaults to overwriting --storyboard")
    parser.add_argument("--narration-output", type=Path, default=Path("narration.txt"))
    parser.add_argument("--subtitle-output", type=Path, default=Path("subtitles.srt"))
    parser.add_argument(
        "--boundary-times",
        help="Comma-separated reviewed internal sentence end times in seconds; required for verified sync",
    )
    args = parser.parse_args()

    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    duration = probe_duration(args.audio)
    reviewed = None
    if args.boundary_times:
        reviewed = [float(value.strip()) for value in args.boundary_times.split(",") if value.strip()]
    scenes = align_scenes(board.get("scenes", []), duration, reviewed)
    board["scenes"] = scenes
    board["target_duration"] = round(duration, 3)
    board["audio_duration"] = round(duration, 3)
    board["timing_source"] = "reviewed_audio_sentence_boundaries" if reviewed is not None else "draft_character_weight_allocation"
    board["timing_verified"] = reviewed is not None
    board_path = args.output_storyboard or args.storyboard
    for path in (board_path, args.narration_output, args.subtitle_output):
        path.parent.mkdir(parents=True, exist_ok=True)
    board_path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.narration_output.write_text(timed_narration(scenes), encoding="utf-8")
    args.subtitle_output.write_text(srt_text(scenes), encoding="utf-8")
    state = "verified boundaries" if reviewed is not None else "DRAFT character weights"
    print(f"Aligned {len(scenes)} sentences to {duration:.3f}s audio using {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
