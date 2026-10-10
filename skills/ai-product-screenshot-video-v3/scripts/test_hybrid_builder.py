#!/usr/bin/env python3
"""Regression checks for the V3 hybrid screenshot/kinetic renderer."""
from __future__ import annotations
import importlib.util
from pathlib import Path

path = Path(__file__).with_name("build_hybrid_hyperframes_project.py")
spec = importlib.util.spec_from_file_location("hybrid", path); assert spec and spec.loader
hybrid = importlib.util.module_from_spec(spec); spec.loader.exec_module(hybrid)

scenes = [
    {"start":0,"duration":3,"narration":"别再只放一张截图。","annotation":{"label":"官方界面"},"kinetic":{"title":"Hybrid V3","features":["动态标题","证据截图"]}},
    {"start":3,"duration":3,"narration":"关注账号。","scene_type":"cta"},
]
for style in hybrid.STYLE_PRESETS:
    html = hybrid.build_html(scenes, 6, "narration.wav", 1080, 1920, [("context.png","focus.jpg"),(None,None)], style)
    assert html.count("<audio ") == 1
    assert f'class="style-{style}"' in html
    assert "title-char" in html and "feature-card" in html and "caption-hot" in html
    for forbidden in ('focus-card", {', 'context-card", {', 'evidence-border", {', 'rotate(', 'skew('):
        assert forbidden not in html, forbidden
    assert "static evidence" not in html.lower()
print("PASS: V3 hybrid builder keeps screenshot evidence static and animates editorial UI")
