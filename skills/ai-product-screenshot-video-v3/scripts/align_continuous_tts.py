#!/usr/bin/env python3
"""Cut one continuous KIE performance into edit references while keeping one master on the render timeline."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import align_timeline as timing


def binary(name: str) -> str:
    value = os.environ.get(f"{name.upper()}_BIN") or shutil.which(name)
    if value:
        return str(value)
    fallback = Path(__file__).with_name(name)
    if fallback.exists():
        return str(fallback)
    raise RuntimeError(f"{name} is required")


def duration(path: Path) -> float:
    value = subprocess.check_output([
        binary("ffprobe"), "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nk=1:nw=1", str(path),
    ], text=True)
    return float(value.strip())


def silence_intervals(path: Path, threshold: str = "-42dB", minimum: float = 0.06) -> list[tuple[float, float]]:
    proc = subprocess.run([
        binary("ffmpeg"), "-hide_banner", "-i", str(path),
        "-af", f"silencedetect=noise={threshold}:d={minimum}", "-f", "null", "-",
    ], text=True, capture_output=True)
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", proc.stderr)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", proc.stderr)]
    return list(zip(starts, ends))


def interval_for(value: float, intervals: list[tuple[float, float]], tolerance: float = 0.025) -> tuple[float, float] | None:
    return next(((start, end) for start, end in intervals if start - tolerance <= value <= end + tolerance), None)


def make_master(source: Path, destination: Path, cta_start: float, cta_duration: float) -> tuple[float, float]:
    source_duration = duration(source)
    raw_cta_duration = source_duration - cta_start
    if raw_cta_duration <= 0:
        raise ValueError("CTA boundary is at or beyond the source audio end")
    tempo = raw_cta_duration / cta_duration
    if not 0.5 <= tempo <= 2.0:
        raise ValueError(f"CTA retime {tempo:.3f}x is outside FFmpeg atempo range")
    destination.parent.mkdir(parents=True, exist_ok=True)
    filters = (
        f"[0:a]atrim=start=0:end={cta_start:.6f},asetpts=PTS-STARTPTS[body];"
        f"[0:a]atrim=start={cta_start:.6f}:end={source_duration:.6f},asetpts=PTS-STARTPTS,"
        f"atempo={tempo:.6f},apad=whole_dur={cta_duration:.6f},atrim=duration={cta_duration:.6f}[cta];"
        "[body][cta]concat=n=2:v=0:a=1[out]"
    )
    subprocess.run([
        binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-filter_complex", filters, "-map", "[out]", "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(destination),
    ], check=True)
    return source_duration, tempo


def cut_segment(master: Path, destination: Path, start: float, end: float) -> None:
    subprocess.run([
        binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(master),
        "-af", f"atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS",
        "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(destination),
    ], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--source-audio", type=Path, required=True)
    parser.add_argument("--output-audio", type=Path, required=True)
    parser.add_argument("--output-storyboard", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--narration-output", type=Path, required=True)
    parser.add_argument("--subtitle-output", type=Path, required=True)
    parser.add_argument("--boundary-times", required=True, help="Reviewed source-audio sentence boundaries, comma-separated")
    parser.add_argument("--task-record", type=Path)
    parser.add_argument("--cta-duration", type=float, default=3.0)
    args = parser.parse_args()

    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    scenes = board.get("scenes") or []
    boundaries = [round(float(value.strip()), 6) for value in args.boundary_times.split(",") if value.strip()]
    if len(boundaries) != len(scenes) - 1:
        raise ValueError(f"expected {len(scenes) - 1} boundaries, got {len(boundaries)}")
    if any(end <= start for start, end in zip([0.0] + boundaries[:-1], boundaries)):
        raise ValueError("boundaries must be strictly increasing")
    if not scenes or scenes[-1].get("scene_type") != "cta":
        raise ValueError("the final scene must be the CTA")

    intervals = silence_intervals(args.source_audio)
    reviewed = []
    for value in boundaries:
        interval = interval_for(value, intervals)
        if interval is None:
            raise ValueError(f"boundary {value:.3f}s is not inside a detected silence interval")
        reviewed.append({"time": round(value, 3), "silence_start": round(interval[0], 3), "silence_end": round(interval[1], 3), "silence_duration": round(interval[1] - interval[0], 3)})

    source_duration, cta_tempo = make_master(args.source_audio, args.output_audio, boundaries[-1], args.cta_duration)
    final_duration = round(duration(args.output_audio), 3)
    # FFmpeg's atempo can add a few samples of filter latency. Anchor the final
    # boundary to the measured master so the authored CTA remains exactly fixed.
    rendered_cta_start = round(final_duration - args.cta_duration, 3)
    final_boundaries = [round(value, 3) for value in boundaries[:-1]] + [rendered_cta_start]
    ends = final_boundaries + [final_duration]
    aligned = []
    previous_end = 0.0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    segment_rows = []
    for index, (scene, end) in enumerate(zip(scenes, ends)):
        item = copy.deepcopy(scene)
        item["start"] = round(previous_end, 3)
        item["end"] = round(end, 3)
        item["duration"] = round(end - previous_end, 3)
        item["subtitle"] = str(item.get("subtitle") or item.get("narration") or "").strip()
        if index < len(reviewed):
            item["boundary_silence"] = reviewed[index]
        if index == len(scenes) - 1:
            item["fixed_duration"] = round(args.cta_duration, 3)
            item["cta_source_duration"] = round(source_duration - boundaries[-1], 3)
            item["cta_postprocess_tempo"] = round(cta_tempo, 6)
        segment_path = args.output_dir / f"{index + 1:03d}-{item.get('id') or f'scene-{index + 1:03d}'}.wav"
        cut_segment(args.output_audio, segment_path, previous_end, end)
        segment_rows.append({
            "id": item.get("id"), "text": item.get("narration"), "path": str(segment_path),
            "start": round(previous_end, 3), "end": round(end, 3), "duration": item["duration"],
            "derived_from_single_master": True,
        })
        aligned.append(item)
        previous_end = end

    task_id = None
    if args.task_record and args.task_record.exists():
        task_id = json.loads(args.task_record.read_text(encoding="utf-8")).get("task_id")
    manifest = {
        "mode": "single_kie_task_continuous_master_with_edit_cuts",
        "task_id": task_id,
        "source_audio": str(args.source_audio),
        "master_audio": str(args.output_audio),
        "source_duration": round(source_duration, 3),
        "master_duration": final_duration,
        "cta_postprocess_tempo": round(cta_tempo, 6),
        "rendered_cta_start": rendered_cta_start,
        "segments_are_edit_references_only": True,
        "render_uses_continuous_master": True,
        "segments": segment_rows,
    }
    (args.output_dir / "segments.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    board["scenes"] = aligned
    board["target_duration"] = final_duration
    board["audio_duration"] = final_duration
    board["timing_source"] = "single_continuous_tts_reviewed_silence_boundaries"
    board["timing_verified"] = True
    board["continuous_tts"] = {
        "single_task": True,
        "task_id": task_id,
        "source_duration": round(source_duration, 3),
        "master_duration": final_duration,
        "render_uses_master": True,
        "cta_only_retime": round(cta_tempo, 6),
        "rendered_cta_start": rendered_cta_start,
    }
    args.output_storyboard.parent.mkdir(parents=True, exist_ok=True)
    args.output_storyboard.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.narration_output.write_text(timing.timed_narration(aligned), encoding="utf-8")
    args.subtitle_output.write_text(timing.srt_text(aligned), encoding="utf-8")
    print(f"Aligned one continuous KIE task into {len(aligned)} edit cuts; render master {final_duration:.3f}s; CTA tempo {cta_tempo:.3f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
