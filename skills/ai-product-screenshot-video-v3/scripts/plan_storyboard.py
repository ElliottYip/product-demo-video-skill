#!/usr/bin/env python3
"""Map Chinese narration paragraphs to verified sources and timed vertical scenes."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def clauses(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[。！？!?；;])\s*|\n+", text) if x.strip()]


def weight(text: str) -> float:
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    words = len(re.findall(r"[A-Za-z0-9]+", text))
    return max(1.0, cjk + 1.7 * words + 4)


def approved_source_ids(review_data: dict) -> set[str]:
    checks = ("evidence_visible", "claim_match", "readable_mobile", "overlays_clear", "privacy_safe")
    return {
        str(review.get("source_id"))
        for review in review_data.get("reviews", [])
        if review.get("status") == "approved"
        and review.get("review_method") == "multimodal_image_inspection"
        and all(review.get(check) is True for check in checks)
        and str(review.get("visible_evidence") or "").strip()
    }


def cta_scene(index: int, start: float, text: str, duration: float) -> dict:
    return {
        "id": f"scene-{index + 1:03d}",
        "scene_type": "cta",
        "start": round(start, 3),
        "duration": round(duration, 3),
        "fixed_duration": round(duration, 3),
        "narration": text.strip(),
        "subtitle": text.strip(),
        "source_id": None,
        "image": None,
        "motion": "static",
        "layout_variant": "cta_background",
        "background_color": "0xF5F7FB",
        "annotation": None,
        "claim_status": "not_applicable",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--narration", type=Path, required=True)
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--reviews", type=Path, help="Required when sources.json mandates multimodal review")
    p.add_argument("--output", type=Path, default=Path("storyboard.json"))
    p.add_argument("--target-duration", type=float, default=30)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--cta-text", default="想看更多实用 AI 工具，记得关注账号。")
    p.add_argument("--cta-duration", type=float, default=3.0)
    p.add_argument("--no-cta", action="store_true", help="Disable the default three-second CTA outro")
    args = p.parse_args()

    lines = clauses(args.narration.read_text(encoding="utf-8"))
    source_data = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = source_data.get("sources", [])
    review_required = bool((source_data.get("research_policy") or {}).get("multimodal_review_required"))
    if review_required:
        if not args.reviews:
            raise SystemExit("--reviews is required by sources.json research policy")
        review_data = json.loads(args.reviews.read_text(encoding="utf-8"))
        approved_ids = approved_source_ids(review_data)
        sources = [source for source in sources if str(source.get("id")) in approved_ids]
    if not lines or not sources:
        raise SystemExit("narration and sources must both be non-empty")
    total_weight = sum(weight(x) for x in lines)
    min_total = 2.0 * len(lines)
    target = max(args.target_duration, min_total)
    motions = ["push_in", "pan_right", "focus_crop", "pan_left"]
    layouts = ["full_page_establishing", "inset_zoom", "documentation_focus", "editorial_evidence"]
    scenes = []
    start = 0.0
    for i, text in enumerate(lines):
        src = next((s for s in sources if s.get("narration", "") in text or text in s.get("narration", "")), None)
        if src is None and review_required:
            raise SystemExit(f"sentence has no semantically mapped approved screenshot: {text}")
        if src is None:
            src = sources[min(i, len(sources) - 1)]
        dur = max(2.0, target * weight(text) / total_weight)
        source_region = src.get("source_region")
        layout = str(src.get("layout_variant") or layouts[i % len(layouts)])
        if layout == "inset_zoom" and not source_region:
            layout = "feature_closeup"
        motion = "focus_crop" if source_region and layout != "full_page_establishing" else motions[i % len(motions)]
        box = src.get("annotation_box") or {}
        annotation = None
        if src.get("annotation_label") or source_region:
            annotation = {
                "type": "feature",
                "x": int(box.get("x", 90)),
                "y": int(box.get("y", 360)),
                "width": int(box.get("width", 880)),
                "height": int(box.get("height", 420)),
                "label": str(src.get("annotation_label") or "重点功能"),
            }
            if source_region:
                annotation["source_region"] = source_region
            if src.get("click"):
                annotation["click"] = src["click"]
        scenes.append({
            "id": f"scene-{i + 1:03d}",
            "start": round(start, 3),
            "duration": round(dur, 3),
            "narration": text,
            "subtitle": text,
            "source_id": src["id"],
            "image": src["screenshot"],
            "motion": motion,
            "layout_variant": layout,
            "annotation": annotation,
            "claim_status": "verified" if src.get("official") else "qualified",
        })
        start += dur
    if not args.no_cta:
        if args.cta_duration <= 0 or not args.cta_text.strip():
            raise SystemExit("CTA text and duration must be positive unless --no-cta is used")
        scenes.append(cta_scene(len(scenes), start, args.cta_text, args.cta_duration))
        start += args.cta_duration
    payload = {
        "schema_version": "1.0",
        "canvas": {"width": args.width, "height": args.height, "fps": args.fps},
        "target_duration": round(start, 3),
        "cta_enabled": not args.no_cta,
        "scenes": scenes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Planned {len(scenes)} scenes / {start:.2f}s -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
