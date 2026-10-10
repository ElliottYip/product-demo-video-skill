#!/usr/bin/env python3
"""Build a screenshot-led kinetic HyperFrames project with static evidence and animated editorial UI."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

HF_VERSION = "0.7.65"
LAYOUTS = ("center-proof", "split-proof", "focus-stage", "proof-poster")
STYLE_PRESETS = {
    "kinetic-dark": {"label":"深色动效科技","bg_a":"#090b18","bg_b":"#05060d","primary":"#8b5cf6","secondary":"#f59e0b","signal":"#14b8a6","text":"#f8fafc","muted":"#c4b5fd","panel":"rgba(30,41,59,.84)","caption":"rgba(2,6,23,.94)"},
    "clean-editorial": {"label":"明亮编辑杂志","bg_a":"#f8fafc","bg_b":"#e8eef7","primary":"#2563eb","secondary":"#d97706","signal":"#0f766e","text":"#0f172a","muted":"#334155","panel":"rgba(255,255,255,.90)","caption":"rgba(15,23,42,.96)"},
    "brand-adaptive": {"label":"品牌自适应","bg_a":"#0b1020","bg_b":"#07111a","primary":"#6366f1","secondary":"#f97316","signal":"#22c55e","text":"#f8fafc","muted":"#c7d2fe","panel":"rgba(17,24,39,.86)","caption":"rgba(3,7,18,.95)"},
    "premium-tech": {"label":"克制高级科技","bg_a":"#08111f","bg_b":"#020617","primary":"#38bdf8","secondary":"#e2e8f0","signal":"#22d3ee","text":"#f8fafc","muted":"#bae6fd","panel":"rgba(15,23,42,.88)","caption":"rgba(2,6,23,.96)"},
    "viral-neon": {"label":"高冲击爆款霓虹","bg_a":"#12051a","bg_b":"#05030a","primary":"#d946ef","secondary":"#facc15","signal":"#2dd4bf","text":"#fff7ed","muted":"#f5d0fe","panel":"rgba(49,17,64,.86)","caption":"rgba(10,2,16,.95)"},
    "evidence-first": {"label":"极简证据优先","bg_a":"#eef2f7","bg_b":"#dbe4ef","primary":"#111827","secondary":"#2563eb","signal":"#059669","text":"#111827","muted":"#334155","panel":"rgba(255,255,255,.94)","caption":"rgba(17,24,39,.97)"},
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def project_path(base: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def crop_focus(source: Path, destination: Path, region: dict | None) -> None:
    if not region:
        shutil.copy2(source, destination)
        return
    try:
        from PIL import Image
    except ImportError:
        shutil.copy2(source, destination)
        return
    x, y = float(region.get("x", 0)), float(region.get("y", 0))
    width, height = float(region.get("width", 1)), float(region.get("height", 1))
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < width <= 1 and 0 < height <= 1 and x + width <= 1.001 and y + height <= 1.001):
        raise ValueError(f"invalid normalized source_region: {region}")
    with Image.open(source) as image:
        px, py = image.size
        pad_x, pad_y = width * 0.05, height * 0.07
        box = (
            max(0, round((x - pad_x) * px)), max(0, round((y - pad_y) * py)),
            min(px, round((x + width + pad_x) * px)), min(py, round((y + height + pad_y) * py)),
        )
        image.crop(box).convert("RGB").save(destination, quality=95)


def kinetic(scene: dict, index: int) -> dict:
    supplied = dict(scene.get("kinetic") or {})
    narration = str(scene.get("subtitle") or scene.get("narration") or "").strip()
    label = str((scene.get("annotation") or {}).get("label") or "").strip()
    english = re.findall(r"[A-Za-z][A-Za-z0-9.-]{1,}", narration)
    supplied.setdefault("ordinal", f"{index + 1:02d}")
    supplied.setdefault("badge", "官方资料 · 已核实")
    supplied.setdefault("title", label or (english[0] if english else narration[:14]))
    supplied.setdefault("tagline", narration)
    supplied.setdefault("takeaway", narration)
    if not supplied.get("features"):
        parts = [part.strip(" ：:，,。；;") for part in re.split(r"[，,：:；;。]", narration) if part.strip()]
        supplied["features"] = parts[:4] or [narration]
    if not supplied.get("highlight_terms"):
        supplied["highlight_terms"] = english[:3] + re.findall(r"\d+(?:\.\d+)?", narration)[:2]
    supplied.setdefault("layout", LAYOUTS[index % len(LAYOUTS)])
    supplied.setdefault("show_evidence", True)
    return supplied


def highlighted(text: str, terms: list[str]) -> str:
    if not terms:
        return esc(text)
    pattern = re.compile("(" + "|".join(re.escape(term) for term in sorted({term for term in terms if term}, key=len, reverse=True)) + ")", re.I)
    pieces = pattern.split(text)
    term_set = {term.lower() for term in terms}
    return "".join(f'<span class="caption-hot">{esc(piece)}</span>' if piece.lower() in term_set else esc(piece) for piece in pieces)


def title_letters(value: str) -> str:
    return "".join(f'<span class="title-char">{esc(char)}</span>' for char in value)


def particles(scene_index: int, count: int = 18) -> str:
    rows = []
    for i in range(count):
        x = (scene_index * 17 + i * 37) % 96 + 2
        y = (scene_index * 29 + i * 53) % 88 + 5
        size = 2 + ((scene_index + i * 3) % 6)
        delay = ((scene_index * 7 + i * 11) % 100) / 100
        rows.append(f'<i class="particle" style="left:{x}%;top:{y}%;width:{size}px;height:{size}px;--phase:{delay:.2f}"></i>')
    return "".join(rows)


def proof_markup(context_name: str | None, focus_name: str | None, label: str) -> str:
    if not context_name or not focus_name:
        return '<div class="proof-placeholder">本镜头为编辑转场；证据记录保存在 sources.json</div>'
    return f'''<div class="context-card"><img src="assets/{esc(context_name)}" alt="official page context" /></div>
          <div class="focus-card"><img src="assets/{esc(focus_name)}" alt="exact official evidence" /><div class="evidence-border"></div><div class="proof-label">{esc(label)}</div></div>'''


def scene_markup(scene: dict, index: int, context_name: str | None, focus_name: str | None) -> str:
    start, duration = float(scene["start"]), float(scene["duration"])
    sid = f"scene-{index + 1:03d}"
    narration = str(scene.get("subtitle") or scene.get("narration") or "").strip()
    if scene.get("scene_type") == "cta":
        return f'''      <section id="{sid}" class="clip cta-scene" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">
        <div class="scene-fill cta-fill"><div class="cta-kicker">下一条继续拆真实 AI 工具</div><div class="search-card"><span>搜索</span><strong>关注账号</strong><b>⌕</b></div><div class="cta-copy">{esc(narration)}</div></div>
      </section>'''
    meta = kinetic(scene, index)
    layout = str(meta["layout"]) if str(meta["layout"]) in LAYOUTS else LAYOUTS[index % len(LAYOUTS)]
    title = str(meta["title"])
    title_length = len(re.sub(r"\s+", "", title))
    title_size = "title-short" if title_length <= 9 else ("title-medium" if title_length <= 15 else "title-long")
    tagline_size = "tagline-long" if len(str(meta["tagline"])) > 28 else ""
    features = [str(value) for value in meta.get("features", [])][:4]
    feature_rows = "".join(f'<div class="feature-card"><i></i><span>{esc(value)}</span></div>' for value in features)
    label = str((scene.get("annotation") or {}).get("label") or "官方证据")
    proof = proof_markup(context_name, focus_name, label) if meta.get("show_evidence", True) else ""
    scene_class = "hook-scene" if index < 2 or scene.get("scene_type") == "hook" else "hybrid-scene"
    return f'''      <section id="{sid}" class="clip {scene_class} layout-{layout}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">
        <div class="scene-fill"><div class="ambient"></div><div class="grid"></div><div class="particles">{particles(index)}</div>
          <div class="topline"><span class="ordinal">{esc(meta['ordinal'])}</span><span class="trust-badge">{esc(meta['badge'])}</span></div>
          <div class="kinetic-title {title_size}">{title_letters(title)}<span class="cursor"></span></div>
          <div class="tagline {tagline_size}">{esc(meta['tagline'])}</div>
          <div class="proof-stage">{proof}</div>
          <div class="feature-grid">{feature_rows}</div>
          <div class="takeaway">{esc(meta['takeaway'])}</div>
          <div class="caption-card">{highlighted(narration, list(meta.get('highlight_terms') or []))}</div>
        </div>
      </section>'''


def timeline_js(scenes: list[dict]) -> str:
    rows = ["      const tl = gsap.timeline({ paused: true });"]
    for index, scene in enumerate(scenes):
        start, duration = float(scene["start"]), float(scene["duration"])
        sid = f"#scene-{index + 1:03d}"
        if scene.get("scene_type") == "cta":
            rows.extend([
                f'tl.from("{sid} .cta-kicker", {{opacity:0,y:-24,duration:.28,ease:"power2.out"}}, {start + .05:.3f});',
                f'tl.from("{sid} .search-card", {{opacity:0,y:34,duration:.38,ease:"power3.out"}}, {start + .24:.3f});',
                f'tl.from("{sid} .cta-copy", {{opacity:0,y:24,duration:.32,ease:"power2.out"}}, {start + .48:.3f});',
            ])
            continue
        reveal_span = min(1.05, max(.42, duration * .24))
        rows.extend([
            f'tl.from("{sid} .ordinal", {{opacity:0,y:-18,duration:.22,ease:"power2.out"}}, {start + .03:.3f});',
            f'tl.from("{sid} .trust-badge", {{opacity:0,x:24,duration:.26,ease:"power2.out"}}, {start + .08:.3f});',
            f'tl.from("{sid} .title-char", {{opacity:0,duration:.01,stagger:{reveal_span:.3f}/Math.max(1, document.querySelectorAll("{sid} .title-char").length)}}, {start + .16:.3f});',
            f'tl.from("{sid} .tagline", {{opacity:0,y:18,duration:.25,ease:"power2.out"}}, {start + .44:.3f});',
            # Screenshot pixels, crop, and evidence border are deliberately absent from the timeline.
            f'tl.from("{sid} .feature-card", {{opacity:0,y:24,duration:.28,stagger:.12,ease:"power3.out"}}, {start + min(1.05, duration * .30):.3f});',
            f'tl.from("{sid} .takeaway", {{opacity:0,y:20,duration:.30,ease:"power2.out"}}, {start + min(1.75, duration * .48):.3f});',
            f'tl.from("{sid} .caption-card", {{opacity:0,y:28,duration:.28,ease:"power3.out"}}, {start + .20:.3f});',
            f'tl.to("{sid} .particle", {{opacity:.85,y:-16,duration:{max(.5, duration - .1):.3f},stagger:.02,ease:"none"}}, {start + .04:.3f});',
        ])
    rows.append('      window.__timelines["main"] = tl;')
    return "\n      ".join(rows)


def build_html(scenes: list[dict], duration: float, audio_name: str, width: int, height: int, media: list[tuple[str | None, str | None]], style_preset: str = "kinetic-dark", theme_override: dict | None = None) -> str:
    markups = [scene_markup(scene, index, *media[index]) for index, scene in enumerate(scenes)]
    if style_preset not in STYLE_PRESETS:
        raise ValueError(f"unknown style preset: {style_preset}")
    theme = dict(STYLE_PRESETS[style_preset])
    for key, value in (theme_override or {}).items():
        if key in theme and key != "label" and isinstance(value, str) and value.strip():
            theme[key] = value.strip()
    variables = ";".join(f"--{key.replace('_','-')}:{value}" for key, value in theme.items() if key != "label")
    return f'''<!doctype html>
<html lang="zh-CN" class="style-{style_preset}"><head><meta charset="UTF-8" /><meta name="viewport" content="width={width}, height={height}" /><title>AI Product Hybrid Video V3</title><script src="./node_modules/gsap/dist/gsap.min.js"></script>
<style>
@font-face{{font-family:"HF CJK";src:local("PingFang SC"),local("Hiragino Sans GB");font-weight:100 900}}:root{{{variables}}}*{{box-sizing:border-box}}html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden;background:var(--bg-b)}}body{{font-family:"HF CJK",sans-serif}}#root{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:var(--bg-b);color:var(--text)}}.clip,.scene-fill{{position:absolute;inset:0;width:{width}px;height:{height}px;overflow:hidden}}.scene-fill{{background:radial-gradient(circle at 52% 30%,color-mix(in srgb,var(--primary) 25%,transparent),transparent 34%),radial-gradient(circle at 80% 72%,color-mix(in srgb,var(--signal) 17%,transparent),transparent 32%),linear-gradient(145deg,var(--bg-a),var(--bg-b) 72%)}}.ambient{{position:absolute;inset:0;background:linear-gradient(120deg,color-mix(in srgb,var(--primary) 9%,transparent),transparent 45%,color-mix(in srgb,var(--secondary) 7%,transparent));}}.grid{{position:absolute;inset:0;opacity:.14;background-image:linear-gradient(rgba(148,163,184,.15) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.15) 1px,transparent 1px);background-size:64px 64px;mask-image:linear-gradient(180deg,transparent,#000 20%,#000 82%,transparent)}}.particle{{position:absolute;display:block;border-radius:50%;background:var(--primary);box-shadow:0 0 16px var(--primary);opacity:.25}}.topline{{position:absolute;z-index:8;left:64px;right:64px;top:68px;display:flex;align-items:center;justify-content:space-between}}.ordinal{{font-size:38px;font-weight:950;color:var(--secondary);letter-spacing:.08em}}.trust-badge{{padding:13px 20px;border:1px solid color-mix(in srgb,var(--secondary) 55%,transparent);border-radius:999px;background:color-mix(in srgb,var(--secondary) 12%,transparent);color:var(--secondary);font-size:22px;font-weight:850}}.kinetic-title{{position:absolute;z-index:7;left:70px;right:70px;top:145px;max-height:126px;overflow:hidden;text-align:center;font-weight:950;line-height:1.02;letter-spacing:-.035em;color:var(--primary);text-shadow:0 0 32px color-mix(in srgb,var(--primary) 35%,transparent)}}.kinetic-title.title-short{{font-size:78px}}.kinetic-title.title-medium{{font-size:65px}}.kinetic-title.title-long{{font-size:54px}}.title-char{{display:inline-block}}.cursor{{display:inline-block;width:5px;height:.9em;margin-left:8px;vertical-align:-.07em;background:var(--text)}}.tagline{{position:absolute;z-index:7;left:90px;right:90px;top:278px;max-height:66px;overflow:hidden;text-align:center;color:var(--secondary);font-size:29px;font-weight:800;line-height:1.2}}.tagline.tagline-long{{font-size:25px}}.proof-stage{{position:absolute;z-index:3;left:56px;right:56px;top:355px;height:680px}}.context-card,.focus-card{{position:absolute;overflow:hidden;background:#fff;border:1px solid rgba(255,255,255,.20);border-radius:26px;box-shadow:0 30px 80px rgba(0,0,0,.34)}}.context-card{{left:0;top:0;width:100%;height:410px}}.focus-card{{left:140px;right:0;top:365px;height:305px}}.context-card img,.focus-card img{{display:block;width:100%;height:100%;object-fit:contain;background:#fff}}.evidence-border{{position:absolute;inset:10px;border:7px solid var(--secondary);border-radius:19px;pointer-events:none}}.proof-label{{position:absolute;left:24px;top:24px;max-width:660px;padding:12px 18px;border-radius:11px;background:#111827;color:#fff;font-size:25px;font-weight:900}}.proof-placeholder{{display:grid;place-items:center;width:100%;height:100%;border:2px dashed color-mix(in srgb,var(--primary) 45%,transparent);border-radius:26px;color:var(--muted);font-size:26px}}.feature-grid{{position:absolute;z-index:6;left:72px;right:72px;top:1060px;display:grid;grid-template-columns:1fr 1fr;gap:18px}}.feature-card{{min-height:105px;display:flex;align-items:center;gap:18px;padding:20px 24px;border:1px solid color-mix(in srgb,var(--primary) 48%,transparent);border-radius:18px;background:var(--panel);box-shadow:inset 0 0 25px color-mix(in srgb,var(--primary) 10%,transparent)}}.feature-card i{{flex:0 0 12px;width:12px;height:12px;border-radius:50%;background:var(--signal);box-shadow:0 0 16px var(--signal)}}.feature-card span{{font-size:29px;font-weight:760;line-height:1.25}}.takeaway{{position:absolute;z-index:6;left:150px;right:150px;top:1298px;min-height:112px;display:grid;place-items:center;padding:20px 28px;text-align:center;border:1px solid color-mix(in srgb,var(--secondary) 50%,transparent);border-radius:18px;background:var(--panel);font-size:30px;font-weight:850;line-height:1.3}}.caption-card{{position:absolute;z-index:9;left:78px;right:78px;bottom:118px;min-height:150px;display:grid;place-items:center;padding:27px 34px;text-align:center;border:1px solid color-mix(in srgb,var(--primary) 45%,transparent);border-radius:22px;background:var(--caption);box-shadow:0 20px 60px rgba(0,0,0,.35);color:#f8fafc;font-size:42px;font-weight:920;line-height:1.28}}.caption-hot{{color:var(--secondary);text-shadow:0 0 18px color-mix(in srgb,var(--secondary) 45%,transparent)}}.layout-split-proof .context-card{{width:68%;height:490px}}.layout-split-proof .focus-card{{left:54%;top:225px;height:440px}}.layout-focus-stage .context-card{{left:190px;width:calc(100% - 190px);height:325px;opacity:.72}}.layout-focus-stage .focus-card{{left:0;right:80px;top:275px;height:395px}}.layout-proof-poster .context-card{{height:350px}}.layout-proof-poster .focus-card{{left:55px;right:55px;top:305px;height:365px}}.hook-scene .kinetic-title{{top:138px;color:var(--text)}}.hook-scene .tagline{{top:278px;color:var(--secondary)}}.hook-scene .proof-stage{{top:365px;height:650px}}.hook-scene .feature-grid{{top:1040px}}.style-evidence-first .kinetic-title{{font-size:62px}}.style-evidence-first .proof-stage{{top:335px;height:740px}}.style-evidence-first .context-card{{height:485px}}.style-evidence-first .focus-card{{top:430px;height:295px}}.style-evidence-first .feature-grid{{top:1100px}}.style-clean-editorial .particle,.style-evidence-first .particle{{opacity:.10}}.cta-fill{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:42px;padding:90px}}.cta-kicker{{font-size:42px;font-weight:850;color:var(--muted)}}.search-card{{width:880px;height:150px;display:grid;grid-template-columns:160px 1fr 100px;align-items:center;padding:0 34px;border-radius:34px;background:#fff;color:#111827;box-shadow:0 25px 80px rgba(0,0,0,.35);font-size:38px}}.search-card span{{font-weight:900}}.search-card strong{{text-align:center;font-weight:780}}.search-card b{{text-align:right;font-size:58px}}.cta-copy{{max-width:850px;text-align:center;font-size:55px;font-weight:950;line-height:1.25;color:var(--text)}}
</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.3f}" data-width="{width}" data-height="{height}" data-fps="30">
{chr(10).join(markups)}
      <audio id="narration-audio" data-start="0.000" data-duration="{duration:.3f}" data-track-index="20" data-volume="1" src="assets/{esc(audio_name)}"></audio>
</div><script>window.__timelines=window.__timelines||{{}};
{timeline_js(scenes)}
</script></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output-project", type=Path, required=True)
    parser.add_argument("--style", choices=("auto", *STYLE_PRESETS.keys()), default="auto")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    scenes = board.get("scenes") or []
    if not scenes:
        raise SystemExit("storyboard has no scenes")
    project = args.output_project.resolve()
    if project.exists() and any(project.iterdir()) and not args.force:
        raise SystemExit("output project is non-empty; pass --force")
    assets, renders = project / "assets", project / "renders"
    assets.mkdir(parents=True, exist_ok=True); renders.mkdir(parents=True, exist_ok=True)
    base = args.storyboard.resolve().parent
    media = []
    for index, scene in enumerate(scenes):
        if scene.get("scene_type") == "cta" or not scene.get("image"):
            media.append((None, None)); continue
        source = project_path(base, str(scene["image"]))
        if not source.exists():
            raise SystemExit(f"missing screenshot for {scene.get('id')}: {source}")
        context_name = f"scene-{index + 1:03d}-context{source.suffix.lower() or '.png'}"
        focus_name = f"scene-{index + 1:03d}-focus.jpg"
        shutil.copy2(source, assets / context_name)
        crop_focus(source, assets / focus_name, (scene.get("annotation") or {}).get("source_region"))
        media.append((context_name, focus_name))
    audio_name = "narration" + (args.audio.suffix.lower() or ".wav")
    shutil.copy2(args.audio.resolve(), assets / audio_name)
    canvas = board.get("canvas") or {}; width, height = int(canvas.get("width", 1080)), int(canvas.get("height", 1920))
    duration = float(board.get("audio_duration") or max(float(s["start"]) + float(s["duration"]) for s in scenes))
    selected_style = str(board.get("style_preset") or "kinetic-dark") if args.style == "auto" else args.style
    if selected_style not in STYLE_PRESETS:
        raise SystemExit(f"unknown storyboard style_preset: {selected_style}")
    generated = {
        "index.html": build_html(scenes, duration, audio_name, width, height, media, selected_style, board.get("theme")),
        "hyperframes.json": json.dumps({"$schema":"https://hyperframes.heygen.com/schema/hyperframes.json","registry":"https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry","paths":{"blocks":"compositions","components":"compositions/components","assets":"assets"},"media":{"autoProxy":True}}, indent=2) + "\n",
        "meta.json": json.dumps({"name":project.name,"composition":"main","width":width,"height":height,"duration":duration,"renderer":"hyperframes","hyperframes_version":HF_VERSION,"style":"screenshot-led-kinetic-hybrid","style_preset":selected_style,"style_label":STYLE_PRESETS[selected_style]["label"]}, ensure_ascii=False, indent=2) + "\n",
        "package.json": json.dumps({"name":project.name,"private":True,"type":"module","scripts":{"check":f"npx --yes hyperframes@{HF_VERSION} check","preview":f"npx --yes hyperframes@{HF_VERSION} preview","render":f"npx --yes hyperframes@{HF_VERSION} render"},"dependencies":{"gsap":"3.14.2"}}, indent=2) + "\n",
    }
    for name, content in generated.items(): (project / name).write_text(content, encoding="utf-8")
    print(f"Built V3 hybrid HyperFrames project: {project} ({len(scenes)} scenes, {duration:.3f}s, style={selected_style})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
