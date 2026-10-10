#!/usr/bin/env python3
"""Validate the generated Hyperframes project contract without rendering."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    errors: list[str] = []
    for name in ("index.html", "hyperframes.json", "meta.json", "package.json"):
        if not (project / name).is_file():
            errors.append(f"missing {name}")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    source = (project / "index.html").read_text(encoding="utf-8")
    required = ["data-composition-id=\"main\"", "data-width=\"1080\"", "data-height=\"1920\"", "window.__timelines[\"main\"]", "gsap.timeline({ paused: true })"]
    for token in required:
        if token not in source:
            errors.append(f"missing contract token: {token}")
    clips = re.findall(r'<section id="([^"]+)" class="clip[^"]*"[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"[^>]*data-track-index="([^"]+)"', source)
    if not clips:
        errors.append("no direct-child timed scene clips")
    ids = [item[0] for item in clips]
    if len(ids) != len(set(ids)):
        errors.append("duplicate scene ids")
    previous_end = 0.0
    for scene_id, start_text, duration_text, track in clips:
        start, duration = float(start_text), float(duration_text)
        if track != "0":
            errors.append(f"{scene_id} must use sequential scene track 0")
        if abs(start - previous_end) > 0.003 or duration <= 0:
            errors.append(f"{scene_id} has a gap, overlap, or non-positive duration")
        previous_end = start + duration
    audio_tags = re.findall(
        r'<audio id="(narration(?:-audio|-[0-9]+))"[^>]*data-start="([^"]+)"[^>]*data-duration="([^"]+)"[^>]*src="assets/([^"]+)"',
        source,
    )
    if not audio_tags:
        errors.append("local root narration audio missing")
    elif len(audio_tags) not in {1, len(clips)}:
        errors.append(f"expected one master narration clip or {len(clips)} sentence clips, found {len(audio_tags)}")
    for audio_id, start_text, duration_text, asset_name in audio_tags:
        if float(start_text) < 0 or float(duration_text) <= 0:
            errors.append(f"{audio_id} has invalid timing")
        if not (project / "assets" / asset_name).is_file():
            errors.append(f"missing local narration asset: {asset_name}")
    for path in re.findall(r'(?:src|href)="assets/([^"]+)"', source):
        if not (project / "assets" / path).is_file():
            errors.append(f"missing local asset: {path}")
    meta = json.loads((project / "meta.json").read_text(encoding="utf-8"))
    if (meta.get("width"), meta.get("height")) != (1080, 1920):
        errors.append("meta.json is not 1080x1920")
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: Hyperframes project contract valid ({len(clips)} scenes, {previous_end:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
