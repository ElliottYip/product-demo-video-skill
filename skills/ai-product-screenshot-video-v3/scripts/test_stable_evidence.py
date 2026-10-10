#!/usr/bin/env python3
"""Regression checks for stable screenshot evidence in generated Hyperframes HTML."""
from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_hyperframes_project.py")
SPEC = importlib.util.spec_from_file_location("builder", MODULE_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def main() -> int:
    scenes = [
        {"start": 0.0, "duration": 2.0, "narration": "测试证据画面"},
        {"start": 2.0, "duration": 3.0, "narration": "关注账号", "scene_type": "cta"},
    ]
    html = builder.build_html(scenes, 5.0, "narration.wav", 1080, 1920, [("context.png", "focus.jpg"), (None, None)])
    forbidden = (
        '.focus-card", { scale:',
        '.focus-card", { opacity:',
        '.evidence-border", {',
        "transform: rotate(",
        "will-change: transform",
    )
    failures = [token for token in forbidden if token in html]
    if failures:
        raise AssertionError(f"unstable or flashing evidence animation returned: {failures}")
    if "8px solid #facc15" not in html:
        raise AssertionError("static evidence border is missing")
    if builder.choose_layout({"narration": "官方定价是一美元"}, 0) != "price-punch":
        raise AssertionError("price narration did not select the price-punch layout")
    if builder.choose_layout({"narration": "别按价格选", "annotation": {"label": "按任务选，不按价格选"}}, 5) == "price-punch":
        raise AssertionError("a non-price conclusion was misclassified as price evidence")
    for index, expected in enumerate(builder.EDITORIAL_LAYOUTS):
        if builder.choose_layout({}, index) != expected:
            raise AssertionError(f"editorial layout cycle skipped {expected}")
    segmented = builder.build_html(
        scenes,
        5.0,
        [
            {"id": "narration-001", "src": "001.wav", "start": 0.0, "duration": 2.0},
            {"id": "narration-002", "src": "002.wav", "start": 2.0, "duration": 3.0},
        ],
        1080,
        1920,
        [("context.png", "focus.jpg"), (None, None)],
    )
    if segmented.count("<audio ") != 2 or 'data-start="2.000"' not in segmented:
        raise AssertionError("segmented audio was not mounted as direct timed clips")
    print("Stable-evidence regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
