#!/usr/bin/env python3
"""Normalize agent/browser research into a provenance-first sources.json."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


POSITIONING_TYPES = {"official_homepage", "official_positioning"}
FEATURE_TYPES = {"official_feature"}
PROOF_TYPES = {"official_ui", "official_demo", "official_documentation", "official_help", "official_changelog"}


def validate_official_coverage(rows: list[dict], products: list[str], require_price_products: set[str]) -> None:
    errors = []
    for product in products:
        product_rows = [row for row in rows if str(row.get("product", "")).strip() == product]
        if len(product_rows) < 4:
            errors.append(f"{product}: require at least 4 official source records")
        if any(not row.get("official") for row in product_rows):
            errors.append(f"{product}: every source must be official")
        if any(not str(row.get("official_basis") or "").strip() for row in product_rows):
            errors.append(f"{product}: every source needs official_basis")
        unique_urls = {
            str(row.get("final_url") or row.get("url") or "").split("#", 1)[0].rstrip("/")
            for row in product_rows
        }
        unique_urls.discard("")
        if len(unique_urls) < 3:
            errors.append(f"{product}: require at least 3 distinct official pages")
        evidence_types = {str(row.get("evidence_type") or "") for row in product_rows}
        if not evidence_types.intersection(POSITIONING_TYPES):
            errors.append(f"{product}: missing official positioning/homepage evidence")
        if not evidence_types.intersection(FEATURE_TYPES):
            errors.append(f"{product}: missing official feature evidence")
        if not evidence_types.intersection(PROOF_TYPES):
            errors.append(f"{product}: missing official UI/demo/docs/help/changelog evidence")
        if product in require_price_products and "official_pricing" not in evidence_types:
            errors.append(f"{product}: price narration requires an official pricing page")
    if errors:
        raise ValueError("; ".join(errors))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--product", action="append", required=True, help="Product name; repeat for roundups")
    p.add_argument("--topic", required=True)
    p.add_argument("--source", type=Path, required=True, help="JSON array of researched source objects")
    p.add_argument("--output", type=Path, default=Path("sources.json"))
    p.add_argument("--require-price", action="append", default=[], help="Product whose narration mentions price; repeat as needed")
    args = p.parse_args()

    rows = load_json(args.source)
    if isinstance(rows, dict):
        rows = rows.get("sources", [])
    if not isinstance(rows, list) or not rows:
        raise SystemExit("source must contain a non-empty JSON array")

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    normalized = []
    for idx, row in enumerate(rows, 1):
        url = str(row.get("url", "")).strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SystemExit(f"source {idx}: valid http(s) URL required")
        product = str(row.get("product") or args.product[0]).strip()
        claim = str(row.get("claim", "")).strip()
        narration = str(row.get("narration", claim)).strip()
        if not claim or not narration:
            raise SystemExit(f"source {idx}: claim and narration are required")
        domain = parsed.netloc.lower().removeprefix("www.")
        item_id = str(row.get("id") or f"src-{idx:03d}")
        item = {
            "id": item_id,
            "product": product,
            "url": url,
            "final_url": str(row.get("final_url") or url),
            "title": str(row.get("title", "")).strip(),
            "publisher": str(row.get("publisher") or domain),
            "accessed_at": str(row.get("accessed_at") or now),
            "evidence_type": str(row.get("evidence_type") or "official_feature"),
            "official": bool(row.get("official", False)),
            "official_basis": str(row.get("official_basis", "")).strip(),
            "claim": claim,
            "narration": narration,
            "screenshot": str(row.get("screenshot") or f"screenshots/{item_id}.png"),
            "capture_mode": str(row.get("capture_mode") or "screenshot"),
            "verification_notes": str(row.get("verification_notes", "")).strip(),
        }
        if row.get("focus_text"):
            item["focus_text"] = str(row["focus_text"])
        if row.get("scroll_y") is not None:
            item["scroll_y"] = int(row["scroll_y"])
        for optional in ("source_region", "annotation_box", "annotation_label", "click", "layout_variant"):
            if row.get(optional) is not None:
                item[optional] = row[optional]
        normalized.append(item)

    try:
        validate_official_coverage(normalized, args.product, set(args.require_price))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    ids = [r["id"] for r in normalized]
    if len(ids) != len(set(ids)):
        raise SystemExit("source ids must be unique")
    payload = {
        "schema_version": "1.0",
        "generated_at": now,
        "topic": args.topic,
        "products": args.product,
        "research_policy": {
            "official_only": True,
            "minimum_records_per_product": 4,
            "minimum_distinct_pages_per_product": 3,
            "required_families": ["positioning", "feature", "ui_demo_or_docs"],
            "price_products": args.require_price,
            "multimodal_review_required": True,
        },
        "sources": normalized,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(normalized)} verified-source records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
