#!/usr/bin/env python3
"""Generate one KIE TTS task per storyboard sentence, then concatenate exact-timed audio."""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import generate_tts as kie


def probe_duration(path: Path) -> float:
    ffprobe = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if not ffprobe:
        fallback = Path(__file__).with_name("ffprobe")
        ffprobe = str(fallback) if fallback.exists() else None
    if not ffprobe:
        raise RuntimeError("ffprobe or the bundled fallback is required")
    value = subprocess.check_output([
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nk=1:nw=1", str(path),
    ], text=True)
    return float(value.strip())


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ai-product-screenshot-video-v2/2.0)",
        "Accept": "audio/*,application/octet-stream;q=0.9,*/*;q=0.1",
    })
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def normalize_segment(source: Path, destination: Path, tempo: float, exact_duration: float | None = None) -> None:
    ffmpeg = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    filters = [
        f"atempo={kie.validate_tempo(tempo):.3f}",
        "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-42dB:stop_periods=-1:stop_duration=0.06:stop_threshold=-42dB",
        "loudnorm=I=-16:TP=-2:LRA=7",
        "apad=pad_dur=0.08",
    ]
    if exact_duration is not None:
        filters.extend([f"apad=whole_dur={exact_duration:.3f}", f"atrim=duration={exact_duration:.3f}"])
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-vn", "-af", ",".join(filters), "-ac", "1", "-ar", "48000",
        "-c:a", "pcm_s16le", str(destination),
    ], check=True)


def create_segment_task(payload: dict, key: str, timeout: int) -> tuple[str, str]:
    created = kie.request_json(kie.CREATE_URL, key, method="POST", body=payload)
    task_id = str((created.get("data") or {}).get("taskId") or "")
    if not task_id:
        raise RuntimeError("KIE did not return a taskId")
    deadline = time.monotonic() + timeout
    delay = 2.5
    while time.monotonic() < deadline:
        time.sleep(delay)
        record = kie.request_json(kie.QUERY_URL + "?" + urllib.parse.urlencode({"taskId": task_id}), key)
        data = record.get("data") or {}
        state = str(data.get("state", "")).lower()
        if state == "success":
            urls = kie.result_urls(record)
            if not urls:
                raise RuntimeError(f"KIE task {task_id} succeeded without a result URL")
            return task_id, urls[0]
        if state == "fail":
            raise RuntimeError(f"KIE task {task_id} failed: {data.get('failCode')} {data.get('failMsg')}")
        delay = min(10.0, delay * 1.35)
    raise TimeoutError(f"KIE task {task_id} exceeded {timeout}s")


def context_for_scene(scenes: list[dict], index: int, base: str) -> str:
    previous = str(scenes[index - 1].get("narration") or "") if index else "（开头）"
    following = str(scenes[index + 1].get("narration") or "") if index + 1 < len(scenes) else "（结尾）"
    addition = f" 当前只生成整条视频的第{index + 1}句。前一句：{previous} 后一句：{following}。保持同一位说话人、同一音色、同一响度和连续语气；只朗读 dialogue_turns 中的当前句。"
    return (base + addition)[:1000]


def concat_segments(paths: list[Path], destination: Path, inter_sentence_gap: float) -> None:
    ffmpeg = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for path in paths:
        command.extend(["-i", str(path)])
    gap_count = max(0, len(paths) - 1) if inter_sentence_gap > 0 else 0
    if gap_count:
        command.extend(["-f", "lavfi", "-t", f"{inter_sentence_gap:.3f}", "-i", "anullsrc=r=48000:cl=mono"])
        gap_input = len(paths)
        split_outputs = "".join(f"[gap{index}]" for index in range(gap_count))
        filters = [f"[{gap_input}:a]asplit={gap_count}{split_outputs}"]
        sequence = []
        for index in range(len(paths)):
            sequence.append(f"[{index}:a]")
            if index < gap_count:
                sequence.append(f"[gap{index}]")
        filters.append("".join(sequence) + f"concat=n={len(sequence)}:v=0:a=1[out]")
    else:
        filters = ["".join(f"[{index}:a]" for index in range(len(paths))) + f"concat=n={len(paths)}:v=0:a=1[out]"]
    command.extend(["-filter_complex", ";".join(filters), "-map", "[out]", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(destination)])
    subprocess.run(command, check=True)


def timed_outputs(board: dict, narration_path: Path, subtitle_path: Path) -> None:
    align = __import__("align_timeline")
    scenes = board["scenes"]
    narration_path.write_text(align.timed_narration(scenes), encoding="utf-8")
    subtitle_path.write_text(align.srt_text(scenes), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-audio", type=Path, required=True)
    parser.add_argument("--output-storyboard", type=Path, required=True)
    parser.add_argument("--narration-output", type=Path, required=True)
    parser.add_argument("--subtitle-output", type=Path, required=True)
    parser.add_argument("--tempo", type=float, default=1.12)
    parser.add_argument("--inter-sentence-gap", type=float, default=0.10, help="Explicit silence between sentence WAVs; default 100 ms")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--resume", action="store_true", help="Reuse completed matching segment files")
    args = parser.parse_args()
    if not 0 <= args.inter_sentence_gap <= 0.5:
        raise ValueError("--inter-sentence-gap must be between 0 and 0.5 seconds")

    key = os.environ.get("KIE_API_KEY")
    if not key:
        raise SystemExit("KIE_API_KEY is not set; no request was sent")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validated = kie.validate(config)
    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    scenes = board.get("scenes") or []
    if not scenes:
        raise ValueError("storyboard has no scenes")
    speaker_id = validated["input"]["speakers"][0]["speaker_id"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "segments.json"
    existing = {}
    if args.resume and manifest_path.exists():
        existing = {item["id"]: item for item in json.loads(manifest_path.read_text(encoding="utf-8")).get("segments", [])}
    manifest = {
        "mode": "one_kie_task_per_storyboard_sentence",
        "model": kie.MODEL,
        "voice": validated["input"]["speakers"][0],
        "temperature": validated["input"].get("temperature", 1),
        "tempo": args.tempo,
        "inter_sentence_gap": args.inter_sentence_gap,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segments": [],
    }
    segment_paths = []
    cumulative = 0.0
    aligned_scenes = []
    for index, scene in enumerate(scenes):
        scene_id = str(scene.get("id") or f"scene-{index + 1:03d}")
        text = str(scene.get("narration") or "").strip()
        if not text:
            raise ValueError(f"{scene_id} has empty narration")
        final_path = args.output_dir / f"{index + 1:03d}-{scene_id}.wav"
        cached = existing.get(scene_id)
        task_id = str((cached or {}).get("task_id") or "")
        if not (args.resume and cached and cached.get("text") == text and final_path.exists()):
            payload = copy.deepcopy(validated)
            payload["input"]["dialogue_turns"] = [{"speaker_id": speaker_id, "text": text}]
            payload["input"]["sample_context"] = context_for_scene(scenes, index, str(payload["input"].get("sample_context") or ""))
            task_id, url = create_segment_task(payload, key, args.timeout)
            downloaded = args.output_dir / f".{index + 1:03d}.download"
            download(url, downloaded)
            exact = float(scene.get("fixed_duration")) if scene.get("scene_type") == "cta" and scene.get("fixed_duration") else None
            normalize_segment(downloaded, final_path, args.tempo, exact_duration=exact)
            downloaded.unlink(missing_ok=True)
        duration = round(probe_duration(final_path), 3)
        item = copy.deepcopy(scene)
        gap_after = round(args.inter_sentence_gap, 3) if index + 1 < len(scenes) else 0.0
        timeline_duration = round(duration + gap_after, 3)
        item["start"] = round(cumulative, 3)
        item["spoken_duration"] = duration
        item["gap_after"] = gap_after
        item["duration"] = timeline_duration
        cumulative = round(cumulative + timeline_duration, 3)
        item["end"] = cumulative
        item["subtitle"] = str(item.get("subtitle") or text).strip()
        aligned_scenes.append(item)
        segment_paths.append(final_path)
        manifest["segments"].append({"id": scene_id, "text": text, "task_id": task_id, "path": str(final_path), "duration": duration})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{index + 1}/{len(scenes)}] {scene_id}: {duration:.3f}s")

    args.output_audio.parent.mkdir(parents=True, exist_ok=True)
    concat_segments(segment_paths, args.output_audio, args.inter_sentence_gap)
    audio_duration = round(probe_duration(args.output_audio), 3)
    gap_count = max(0, len(aligned_scenes) - 1)
    if gap_count:
        spoken_total = sum(float(scene["spoken_duration"]) for scene in aligned_scenes)
        effective_gap = round(max(0.0, (audio_duration - spoken_total) / gap_count), 3)
        cumulative = 0.0
        for index, item in enumerate(aligned_scenes):
            gap_after = effective_gap if index + 1 < len(aligned_scenes) else 0.0
            item["start"] = round(cumulative, 3)
            item["gap_after"] = gap_after
            item["duration"] = round(float(item["spoken_duration"]) + gap_after, 3)
            cumulative = round(cumulative + float(item["duration"]), 3)
            item["end"] = cumulative
    else:
        effective_gap = 0.0
    board["scenes"] = aligned_scenes
    board["target_duration"] = round(cumulative, 3)
    board["audio_duration"] = audio_duration
    board["timing_source"] = "one_tts_file_per_sentence"
    board["requested_inter_sentence_gap"] = round(args.inter_sentence_gap, 3)
    board["inter_sentence_gap"] = effective_gap
    board["timing_verified"] = True
    args.output_storyboard.parent.mkdir(parents=True, exist_ok=True)
    args.output_storyboard.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    timed_outputs(board, args.narration_output, args.subtitle_output)
    print(f"Segmented narration: {args.output_audio} ({board['audio_duration']:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
