#!/usr/bin/env python3
"""Build an editable Hyperframes project from a reviewed screenshot storyboard."""
from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

HF_VERSION = "0.7.65"
EDITORIAL_LAYOUTS = ("stacked", "split-right", "poster", "split-left", "wide-focus", "context-first")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def project_path(base: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def crop_focus(source: Path, destination: Path, region: dict | None) -> bool:
    if not region:
        shutil.copy2(source, destination)
        return False
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(source, destination)
        return False
    x = float(region.get("x", 0))
    y = float(region.get("y", 0))
    width = float(region.get("width", 1))
    height = float(region.get("height", 1))
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < width <= 1 and 0 < height <= 1 and x + width <= 1.001 and y + height <= 1.001):
        raise ValueError(f"invalid normalized source_region: {region}")
    with Image.open(source) as image:
        px, py = image.size
        padding_x = width * 0.06
        padding_y = height * 0.08
        left = max(0, round((x - padding_x) * px))
        top = max(0, round((y - padding_y) * py))
        right = min(px, round((x + width + padding_x) * px))
        bottom = min(py, round((y + height + padding_y) * py))
        image.crop((left, top, right, bottom)).convert("RGB").save(destination, quality=94)
    return True


def choose_layout(scene: dict, index: int) -> str:
    """Vary orthogonal geometry while keeping every screenshot axis-aligned."""
    requested = str(scene.get("layout_variant") or "").strip().lower().replace("_", "-")
    if requested in {*EDITORIAL_LAYOUTS, "price-punch"}:
        return requested
    label = str((scene.get("annotation") or {}).get("label") or "")
    narration = str(scene.get("narration") or "")
    if label.startswith("官方价格") or any(token in narration for token in ("美元", "每百万输入", "官方定价")):
        return "price-punch"
    return EDITORIAL_LAYOUTS[index % len(EDITORIAL_LAYOUTS)]


def scene_markup(scene: dict, index: int, context_name: str | None, focus_name: str | None) -> str:
    start = float(scene["start"])
    duration = float(scene["duration"])
    scene_id = f"scene-{index + 1:03d}"
    narration = esc(scene.get("subtitle") or scene.get("narration") or "")
    annotation = scene.get("annotation") or {}
    label = esc(annotation.get("label") or "官方证据")
    layout = choose_layout(scene, index)
    if scene.get("scene_type") == "cta":
        return f'''      <section id="{scene_id}" class="clip cta-scene" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">
        <div class="cta-fill scene-fill"><div class="cta-caption">{narration}</div></div>
      </section>'''
    if not context_name or not focus_name:
        raise ValueError(f"{scene_id} has no local screenshot")
    badge = "OFFICIAL · VERIFIED"
    return f'''      <section id="{scene_id}" class="clip evidence-scene layout-{layout}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">
        <div class="scene-fill">
          <div class="blur-bg" data-layout-allow-overflow style="background-image:url('assets/{esc(context_name)}')"></div>
          <div class="shade"></div>
          <div class="topline"><span>{badge}</span><span>{index + 1:02d}</span></div>
          <div class="context-card"><img src="assets/{esc(context_name)}" alt="official page context" /></div>
          <div class="focus-card">
            <img src="assets/{esc(focus_name)}" alt="exact official evidence" />
            <div class="evidence-border"></div>
            <div class="evidence-label">{label}</div>
          </div>
          <div class="caption-card"><span class="caption-accent"></span><div>{narration}</div></div>
        </div>
      </section>'''


def timeline_js(scenes: list[dict]) -> str:
    rows = ["      const tl = gsap.timeline({ paused: true });"]
    for index, scene in enumerate(scenes):
        start = float(scene["start"])
        duration = float(scene["duration"])
        scene_id = f"#scene-{index + 1:03d}"
        if scene.get("scene_type") == "cta":
            rows.append(f'      tl.from("{scene_id} .cta-caption", {{ opacity: 0, y: 36, duration: 0.42, ease: "power3.out" }}, {start + 0.08:.3f});')
            continue
        # Evidence pixels must remain stable. Animating a raster screenshot with
        # fractional scale/rotation makes Chromium resample it every frame and
        # reads as camera shake in a vertical export. The highlight is evidence,
        # not decoration, so it is present from frame one and never flashes.
        rows.extend([
            f'      tl.from("{scene_id} .topline", {{ opacity: 0, y: -20, duration: 0.28, ease: "power2.out" }}, {start + 0.04:.3f});',
            f'      tl.from("{scene_id} .caption-card", {{ opacity: 0, y: 44, duration: 0.36, ease: "power3.out" }}, {start + 0.36:.3f});',
        ])
    rows.append('      window.__timelines["main"] = tl;')
    return "\n".join(rows)


def build_html(scenes: list[dict], duration: float, audio_entries: str | list[dict], width: int, height: int, media: list[tuple[str | None, str | None]]) -> str:
    markups = [scene_markup(scene, index, *media[index]) for index, scene in enumerate(scenes)]
    timeline = timeline_js(scenes)
    if isinstance(audio_entries, str):
        audio_entries = [{"id": "narration-audio", "src": audio_entries, "start": 0.0, "duration": duration}]
    audio_markup = []
    for entry in audio_entries:
        audio_markup.append(
            f'      <audio id="{esc(entry["id"])}" data-start="{float(entry["start"]):.3f}" '
            f'data-duration="{float(entry["duration"]):.3f}" data-track-index="20" data-volume="1" '
            f'src="assets/{esc(entry["src"])}"></audio>'
        )
    return f'''<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={width}, height={height}" />
    <title>AI Product Screenshot Video V2</title>
    <script src="./node_modules/gsap/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "HF CJK"; src: local("Hiragino Sans GB"), local("PingFang SC"); font-style: normal; font-weight: 100 900; }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; background: #eef2f7; }}
      body {{ font-family: "HF CJK", sans-serif; }}
      #root {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; background: #eef2f7; color: #101828; }}
      .clip {{ position: absolute; inset: 0; width: {width}px; height: {height}px; overflow: hidden; }}
      .scene-fill {{ position: absolute; inset: 0; overflow: hidden; background: #eef2f7; }}
      .blur-bg {{ position: absolute; inset: -90px; width: calc(100% + 180px); height: calc(100% + 180px); background-size: cover; background-position: center; filter: blur(34px) saturate(.72); opacity: .42; transform: scale(1.08); }}
      .shade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(248,250,252,.78), rgba(238,242,247,.95) 62%, #eef2f7 100%); }}
      .topline {{ position: absolute; z-index: 8; left: 64px; right: 64px; top: 72px; display: flex; justify-content: space-between; font-size: 23px; font-weight: 800; letter-spacing: .10em; }}
      .topline span:first-child {{ padding: 12px 18px; color: #fff; background: #101828; border-radius: 11px; }}
      .context-card, .focus-card {{ position: absolute; z-index: 3; background: #fff; border-radius: 28px; box-shadow: 0 34px 90px rgba(15,23,42,.20); overflow: hidden; }}
      .context-card {{ left: 74px; top: 190px; width: 932px; height: 520px; border: 1px solid rgba(15,23,42,.12); }}
      .context-card img {{ width: 100%; height: 100%; object-fit: contain; background: #fff; }}
      .focus-card {{ left: 116px; top: 665px; width: 848px; height: 600px; padding: 18px; }}
      .focus-card img {{ display: block; width: 100%; height: 100%; object-fit: contain; border-radius: 17px; background: #fff; }}
      .evidence-border {{ position: absolute; inset: 12px; border: 8px solid #facc15; border-radius: 22px; pointer-events: none; }}
      .evidence-label {{ position: absolute; left: 28px; top: 28px; max-width: 720px; padding: 14px 20px; color: white; background: #101828; border-radius: 12px; font-size: 30px; font-weight: 900; }}
      .caption-card {{ position: absolute; z-index: 7; left: 66px; right: 66px; bottom: 268px; min-height: 230px; display: flex; align-items: center; gap: 24px; padding: 38px 42px; color: white; background: rgba(16,24,40,.96); border-radius: 30px; box-shadow: 0 28px 76px rgba(15,23,42,.28); font-size: 49px; font-weight: 900; line-height: 1.30; letter-spacing: -.025em; }}
      .caption-accent {{ display: block; flex: 0 0 9px; align-self: stretch; width: 9px; border-radius: 9px; background: #facc15; }}
      .layout-split-right .context-card {{ left: 48px; width: 690px; height: 540px; }}
      .layout-split-right .focus-card {{ left: 470px; top: 610px; width: 550px; height: 680px; }}
      .layout-split-right .caption-card {{ left: 66px; right: 210px; }}
      .layout-poster .context-card {{ top: 166px; height: 480px; opacity: .92; }}
      .layout-poster .focus-card {{ left: 82px; top: 610px; width: 916px; height: 680px; }}
      .layout-poster .caption-card {{ left: 110px; right: 110px; bottom: 246px; }}
      .layout-split-left .context-card {{ left: 360px; width: 670px; height: 540px; }}
      .layout-split-left .focus-card {{ left: 60px; top: 610px; width: 570px; height: 680px; }}
      .layout-split-left .caption-card {{ left: 210px; right: 66px; }}
      .layout-wide-focus .context-card {{ left: 250px; top: 172px; width: 780px; height: 430px; }}
      .layout-wide-focus .focus-card {{ left: 45px; top: 555px; width: 990px; height: 720px; }}
      .layout-wide-focus .caption-card {{ border: 3px solid #facc15; }}
      .layout-context-first .context-card {{ left: 45px; top: 170px; width: 990px; height: 610px; }}
      .layout-context-first .focus-card {{ left: 150px; top: 730px; width: 780px; height: 500px; }}
      .layout-context-first .caption-card {{ color: #101828; background: rgba(255,255,255,.97); border: 2px solid rgba(15,23,42,.14); }}
      .layout-context-first .caption-accent {{ background: #101828; }}
      .layout-price-punch .context-card {{ left: 120px; top: 188px; width: 840px; height: 430px; }}
      .layout-price-punch .focus-card {{ left: 62px; top: 590px; width: 956px; height: 650px; }}
      .layout-price-punch .evidence-label {{ font-size: 36px; }}
      .layout-price-punch .caption-card {{ left: 86px; right: 86px; background: #101828; border-bottom: 10px solid #facc15; }}
      .cta-fill {{ display: grid; place-items: center; padding: 100px; background: #eef2f7; }}
      .cta-caption {{ max-width: 870px; text-align: center; color: #101828; font-size: 58px; line-height: 1.28; font-weight: 900; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.3f}" data-width="{width}" data-height="{height}" data-fps="30">
{chr(10).join(markups)}
{chr(10).join(audio_markup)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
{timeline}
    </script>
  </body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--audio-segments-manifest", type=Path, help="Use exact per-scene WAVs from generate_segmented_tts.py")
    parser.add_argument("--output-project", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite generated project files, never unrelated files")
    args = parser.parse_args()
    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    scenes = board.get("scenes") or []
    if not scenes:
        raise SystemExit("storyboard has no scenes")
    project = args.output_project.resolve()
    if project.exists() and any(project.iterdir()) and not args.force:
        raise SystemExit("output project is non-empty; pass --force to replace generated files")
    assets = project / "assets"
    renders = project / "renders"
    assets.mkdir(parents=True, exist_ok=True)
    renders.mkdir(parents=True, exist_ok=True)
    storyboard_base = args.storyboard.resolve().parent
    media: list[tuple[str | None, str | None]] = []
    for index, scene in enumerate(scenes):
        if scene.get("scene_type") == "cta":
            media.append((None, None))
            continue
        source = project_path(storyboard_base, scene.get("image") or "")
        if not source.exists():
            raise SystemExit(f"missing screenshot for {scene.get('id')}: {source}")
        context_name = f"scene-{index + 1:03d}-context{source.suffix.lower() or '.png'}"
        focus_name = f"scene-{index + 1:03d}-focus.jpg"
        shutil.copy2(source, assets / context_name)
        crop_focus(source, assets / focus_name, (scene.get("annotation") or {}).get("source_region"))
        media.append((context_name, focus_name))
    audio_entries: str | list[dict]
    if args.audio_segments_manifest:
        segment_manifest = json.loads(args.audio_segments_manifest.read_text(encoding="utf-8"))
        by_id = {str(item.get("id")): item for item in segment_manifest.get("segments", [])}
        audio_entries = []
        for index, scene in enumerate(scenes):
            scene_id = str(scene.get("id") or f"scene-{index + 1:03d}")
            segment = by_id.get(scene_id)
            if not segment:
                raise SystemExit(f"audio segment missing for {scene_id}")
            source_audio = Path(str(segment.get("path") or "")).resolve()
            if not source_audio.exists():
                raise SystemExit(f"audio segment file missing for {scene_id}: {source_audio}")
            audio_name = f"audio-{index + 1:03d}{source_audio.suffix.lower() or '.wav'}"
            shutil.copy2(source_audio, assets / audio_name)
            scene_duration = float(scene["duration"])
            segment_duration = float(segment["duration"])
            if abs(scene_duration - segment_duration) > 0.015:
                raise SystemExit(f"audio/storyboard duration mismatch for {scene_id}: {segment_duration:.3f}s vs {scene_duration:.3f}s")
            audio_entries.append({"id": f"narration-{index + 1:03d}", "src": audio_name, "start": float(scene["start"]), "duration": scene_duration})
        # Keep the concatenated master as a source deliverable, but do not put it on the render timeline.
        master_name = "narration-master" + (args.audio.suffix.lower() or ".wav")
        shutil.copy2(args.audio.resolve(), assets / master_name)
    else:
        audio_name = "narration" + (args.audio.suffix.lower() or ".wav")
        shutil.copy2(args.audio.resolve(), assets / audio_name)
        audio_entries = audio_name
    canvas = board.get("canvas") or {}
    width = int(canvas.get("width", 1080))
    height = int(canvas.get("height", 1920))
    duration = float(board.get("audio_duration") or max(float(s.get("start", 0)) + float(s.get("duration", 0)) for s in scenes))
    index_html = build_html(scenes, duration, audio_entries, width, height, media)
    generated = {
        "index.html": index_html,
        "hyperframes.json": json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json", "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry", "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True}}, indent=2) + "\n",
        "meta.json": json.dumps({"name": project.name, "composition": "main", "width": width, "height": height, "duration": duration, "renderer": "hyperframes", "hyperframes_version": HF_VERSION}, ensure_ascii=False, indent=2) + "\n",
        "package.json": json.dumps({"name": project.name, "private": True, "type": "module", "scripts": {"check": f"npx --yes hyperframes@{HF_VERSION} check", "preview": f"npx --yes hyperframes@{HF_VERSION} preview", "render": f"npx --yes hyperframes@{HF_VERSION} render"}, "dependencies": {"gsap": "3.14.2"}}, indent=2) + "\n",
    }
    for name, content in generated.items():
        (project / name).write_text(content, encoding="utf-8")
    print(f"Built Hyperframes project: {project} ({len(scenes)} scenes, {duration:.3f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
