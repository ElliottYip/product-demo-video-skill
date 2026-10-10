#!/usr/bin/env python3
"""Apply reviewed image, crop, and kinetic metadata overrides while preserving scene timing."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def merge(target: dict, patch: dict) -> dict:
    result = dict(target)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--overrides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    payload = json.loads(args.overrides.read_text(encoding="utf-8"))
    scene_overrides = payload.get("scenes") or {}
    seen = set()
    board["style_preset"] = payload.get("style_preset", board.get("style_preset", "kinetic-dark"))
    if payload.get("theme"):
        board["theme"] = merge(board.get("theme") or {}, payload["theme"])
    for index, scene in enumerate(board.get("scenes") or []):
        scene_id = str(scene.get("id") or f"scene-{index + 1:03d}")
        if scene_id in scene_overrides:
            board["scenes"][index] = merge(scene, scene_overrides[scene_id])
            seen.add(scene_id)
    missing = sorted(set(scene_overrides) - seen)
    if missing:
        raise SystemExit(f"override scene IDs not found: {', '.join(missing)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Applied {len(seen)} reviewed media override(s): {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
