#!/usr/bin/env python3
"""Validate human/agent multimodal screenshot reviews before storyboard use."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


CHECKS = ("evidence_visible", "claim_match", "readable_mobile", "overlays_clear", "privacy_safe")


def review_errors(sources: list[dict], review_data: dict, required_ids: set[str]) -> list[str]:
    errors = []
    source_by_id = {str(source.get("id")): source for source in sources}
    reviews = review_data.get("reviews", [])
    by_id = {}
    for review in reviews:
        source_id = str(review.get("source_id") or "")
        if source_id in by_id:
            errors.append(f"{source_id}: duplicate screenshot review")
        by_id[source_id] = review
    for source_id in sorted(required_ids):
        if source_id not in source_by_id:
            errors.append(f"{source_id}: review references unknown source")
            continue
        review = by_id.get(source_id)
        if not review:
            errors.append(f"{source_id}: missing multimodal screenshot review")
            continue
        if review.get("review_method") != "multimodal_image_inspection":
            errors.append(f"{source_id}: review_method must be multimodal_image_inspection")
        if review.get("status") != "approved":
            errors.append(f"{source_id}: screenshot is not approved")
        for check in CHECKS:
            if review.get(check) is not True:
                errors.append(f"{source_id}: {check} must be true")
        if not str(review.get("visible_evidence") or "").strip():
            errors.append(f"{source_id}: visible_evidence description is required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--storyboard", type=Path, help="Validate only screenshots used by non-CTA scenes")
    args = parser.parse_args()

    source_data = json.loads(args.sources.read_text(encoding="utf-8"))
    review_data = json.loads(args.reviews.read_text(encoding="utf-8"))
    sources = source_data.get("sources", [])
    if args.storyboard:
        board = json.loads(args.storyboard.read_text(encoding="utf-8"))
        required_ids = {
            str(scene.get("source_id")) for scene in board.get("scenes", [])
            if scene.get("scene_type") != "cta" and scene.get("source_id")
        }
    else:
        required_ids = {str(source.get("id")) for source in sources}
    errors = review_errors(sources, review_data, required_ids)
    if errors:
        print("FAIL\n- " + "\n- ".join(errors))
        return 1
    print(f"PASS: {len(required_ids)} screenshots have approved multimodal evidence reviews")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
