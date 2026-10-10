#!/usr/bin/env python3
"""Validate the required package, JSON links, audio, and final vertical MP4."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


REQUIRED = ["narration.txt", "subtitles.srt", "storyboard.json", "sources.json", "tts-config.json", "screenshots", "audio"]


def short_seconds(value: str) -> float:
    minutes, rest = value.split(":")
    return int(minutes) * 60 + float(rest)


def srt_seconds(value: str) -> float:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--expected-width", type=int, default=1080)
    p.add_argument("--expected-height", type=int, default=1920)
    p.add_argument("--min-duration", type=float, default=1)
    p.add_argument("--video-name", default="final.mp4", help="Defaults to the contractual final.mp4; override only for pipeline tests")
    args = p.parse_args()

    root = args.output_dir.resolve()
    errors = []
    for name in REQUIRED:
        if not (root / name).exists():
            errors.append(f"missing {name}")
    if not (root / args.video_name).exists():
        errors.append(f"missing {args.video_name}")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1

    try:
        board = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
        sources = json.loads((root / "sources.json").read_text(encoding="utf-8"))
        tts = json.loads((root / "tts-config.json").read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON: {exc}")
        board, sources, tts = {}, {}, {}
    def forbidden_secret_key(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower().replace("-", "_") in {"kie_api_key", "api_key", "authorization", "bearer_token"}:
                    return True
                if forbidden_secret_key(child):
                    return True
        elif isinstance(value, list):
            return any(forbidden_secret_key(x) for x in value)
        return False
    if forbidden_secret_key(tts):
        errors.append("tts-config.json contains a forbidden secret field")
    source_ids = {s.get("id") for s in sources.get("sources", [])}
    scenes = board.get("scenes", [])
    used_source_ids = {
        str(scene.get("source_id")) for scene in scenes
        if scene.get("scene_type") != "cta" and scene.get("source_id")
    }
    if (sources.get("research_policy") or {}).get("multimodal_review_required"):
        review_path = root / "screenshot-reviews.json"
        if not review_path.exists():
            errors.append("missing screenshot-reviews.json required by research policy")
        else:
            try:
                review_data = json.loads(review_path.read_text(encoding="utf-8"))
                review_by_id = {str(review.get("source_id")): review for review in review_data.get("reviews", [])}
                for source_id in used_source_ids:
                    review = review_by_id.get(source_id)
                    if not review or review.get("status") != "approved" or review.get("review_method") != "multimodal_image_inspection":
                        errors.append(f"scene source {source_id} lacks approved multimodal screenshot review")
                        continue
                    for check in ("evidence_visible", "claim_match", "readable_mobile", "overlays_clear", "privacy_safe"):
                        if review.get(check) is not True:
                            errors.append(f"scene source {source_id} failed screenshot review check: {check}")
            except Exception as exc:
                errors.append(f"invalid screenshot-reviews.json: {exc}")
    narration_pattern = re.compile(r"^\[(\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}\.\d{3}) \| (\d+\.\d{3})秒\] (.+)$")
    narration_lines = [line for line in (root / "narration.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    narration_matches = [narration_pattern.match(line) for line in narration_lines]
    if len(narration_lines) != len(scenes) or any(match is None for match in narration_matches):
        errors.append("narration timing check failed: require one [start --> end | duration秒] line per scene")
    subtitle_ranges = re.findall(r"(?m)^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$", (root / "subtitles.srt").read_text(encoding="utf-8"))
    if len(subtitle_ranges) != len(scenes):
        errors.append("subtitle timing check failed: SRT range count does not match sentence scenes")
    previous_end = 0.0
    for index, scene in enumerate(scenes):
        is_cta = scene.get("scene_type") == "cta"
        if is_cta:
            if index != len(scenes) - 1 or scene.get("layout_variant") != "cta_background":
                errors.append("CTA must be the final cta_background scene")
            if scene.get("image") is not None or scene.get("annotation") is not None:
                errors.append("CTA background scene must not contain screenshot evidence or annotations")
            if abs(float(scene.get("fixed_duration", 0)) - 3.0) > 0.002:
                errors.append("default CTA fixed duration must be 3.000 seconds")
        else:
            if scene.get("source_id") not in source_ids:
                errors.append(f"scene {scene.get('id')} has unknown source_id")
            image = Path(str(scene.get("image", "")))
            if not image.is_absolute():
                image = root / image
            if not image.exists():
                errors.append(f"scene {scene.get('id')} image missing: {image}")
        start = float(scene.get("start", -1))
        end = float(scene.get("end", start + float(scene.get("duration", 0))))
        duration_value = float(scene.get("duration", 0))
        if abs(start - previous_end) > 0.002 or end <= start or abs((end - start) - duration_value) > 0.002:
            errors.append(f"scene {scene.get('id')} has a gap, overlap, or inconsistent sentence duration")
        if index < len(narration_matches) and narration_matches[index] is not None:
            match = narration_matches[index]
            if abs(short_seconds(match.group(1)) - start) > 0.002 or abs(short_seconds(match.group(2)) - end) > 0.002 or abs(float(match.group(3)) - duration_value) > 0.002:
                errors.append(f"scene {scene.get('id')} narration.txt timing does not match storyboard")
        if index < len(subtitle_ranges):
            subtitle_start, subtitle_end = subtitle_ranges[index]
            if abs(srt_seconds(subtitle_start) - start) > 0.002 or abs(srt_seconds(subtitle_end) - end) > 0.002:
                errors.append(f"scene {scene.get('id')} subtitles.srt timing does not match storyboard")
        previous_end = end
    if len(scenes) >= 3:
        layouts = {s.get("layout_variant") for s in scenes if s.get("layout_variant")}
        if len(layouts) < 2:
            errors.append("visual variety check failed: fewer than two layout variants")
        functional = [scene for scene in scenes[1:] if scene.get("scene_type") != "cta"]
        annotated = [s for s in functional if isinstance(s.get("annotation"), dict) and s["annotation"].get("label")]
        if len(annotated) < max(1, len(functional) - 1):
            errors.append("evidence annotation check failed: most functional scenes need a visible label/box")
    if board.get("cta_enabled") and (not scenes or scenes[-1].get("scene_type") != "cta"):
        errors.append("cta_enabled requires a final CTA scene")

    ffprobe = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe")
    if not ffprobe:
        errors.append("ffprobe unavailable; set FFPROBE_BIN")
    else:
        proc = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(root / args.video_name)], text=True, capture_output=True)
        if proc.returncode:
            errors.append(f"final.mp4 does not decode: {proc.stderr.strip()}")
        else:
            meta = json.loads(proc.stdout)
            streams = meta.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video"), None)
            audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
            if not video:
                errors.append("final.mp4 has no video stream")
            elif (int(video.get("width", 0)), int(video.get("height", 0))) != (args.expected_width, args.expected_height):
                errors.append(f"wrong resolution: {video.get('width')}x{video.get('height')}")
            if not audio:
                errors.append("final.mp4 has no audio stream")
            duration = float((meta.get("format") or {}).get("duration") or 0)
            if duration < args.min_duration:
                errors.append(f"duration too short: {duration:.2f}s")
            if scenes and abs(duration - previous_end) > 0.1:
                errors.append(f"timeline/video duration mismatch: timeline {previous_end:.3f}s vs video {duration:.3f}s")

    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: required package complete; {args.video_name} is {args.expected_width}x{args.expected_height} with audio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
