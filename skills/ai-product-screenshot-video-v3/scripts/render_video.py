#!/usr/bin/env python3
"""Render screenshot scenes, Chinese ASS subtitles, and narration to a vertical MP4."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path


def binary(env: str, name: str) -> str:
    found = os.environ.get(env) or shutil.which(name)
    if not found:
        raise SystemExit(f"{name} not found; set {env}")
    return found


def probe_duration(ffprobe: str, path: Path) -> float:
    out = subprocess.check_output([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)], text=True)
    return float(out.strip())


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def visual_units(text: str) -> float:
    return sum(1.0 if unicodedata.east_asian_width(char) in {"W", "F", "A"} else 0.55 for char in text)


def wrap_subtitle(text: str, max_units: float = 16.5) -> str:
    """Wrap CJK by visual width because libass may not break unspaced Chinese text."""
    lines, current = [], []
    units = 0.0
    break_chars = set("，。！？；、,.!?;：: ")
    for char in text.strip():
        char_units = 1.0 if unicodedata.east_asian_width(char) in {"W", "F", "A"} else 0.55
        if char in break_chars and current and units + char_units > max_units:
            current.append(char)
            lines.append("".join(current).strip())
            current, units = [], 0.0
            continue
        if current and units + char_units > max_units:
            preferred = max((i for i, c in enumerate(current) if c in break_chars), default=-1)
            if preferred >= max(4, len(current) // 2):
                lines.append("".join(current[: preferred + 1]).strip())
                current = current[preferred + 1 :]
                units = visual_units("".join(current))
            else:
                lines.append("".join(current).strip())
                current, units = [], 0.0
        current.append(char)
        units += char_units
    if current:
        lines.append("".join(current).strip())
    return "\n".join(line for line in lines if line)


def build_foreground_filter(motion: str, region: dict | None, width: int, height: int) -> str:
    if motion == "focus_crop" and region:
        x = float(region.get("x", 0))
        y = float(region.get("y", 0))
        w = float(region.get("width", 1))
        h = float(region.get("height", 1))
        if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.001 and y + h <= 1.001):
            raise ValueError("annotation.source_region must stay inside normalized image bounds")
        return (
            f"crop=iw*{w:.6f}:ih*{h:.6f}:x=iw*{x:.6f}:y=ih*{y:.6f},"
            "scale=960:900:force_original_aspect_ratio=increase,"
            "crop=960:900"
        )
    return f"scale={width-120}:{height-610}:force_original_aspect_ratio=decrease"


def build_inset_zoom_filter(region: dict, width: int, height: int) -> str:
    x = float(region.get("x", 0))
    y = float(region.get("y", 0))
    w = float(region.get("width", 1))
    h = float(region.get("height", 1))
    if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.001 and y + h <= 1.001):
        raise ValueError("annotation.source_region must stay inside normalized image bounds")
    return (
        "[0:v]scale=900:560:force_original_aspect_ratio=decrease[context];"
        f"[0:v]crop=iw*{w:.6f}:ih*{h:.6f}:x=iw*{x:.6f}:y=ih*{y:.6f},"
        "scale=800:520:force_original_aspect_ratio=increase,crop=800:520,"
        "pad=820:540:10:10:color=0xF8FAFC[detail];"
    )


def build_motion_filter(motion: str, frames: int, width: int, height: int) -> str:
    doubled = f"scale={width * 2}:{height * 2}"
    progress = f"on/{max(1, frames - 1)}"
    if motion == "pan_left":
        z = "1.045"
        x = f"(iw-iw/zoom)*(0.80-0.60*{progress})"
    elif motion == "pan_right":
        z = "1.045"
        x = f"(iw-iw/zoom)*(0.20+0.60*{progress})"
    else:
        step = 0.00016 if motion == "focus_crop" else 0.00024
        z = f"min(1+on*{step:.5f},1.045)"
        x = "(iw-iw/zoom)/2"
    y = "(ih-ih/zoom)/2"
    return f"{doubled},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps=30"


def _filter_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def build_annotation_filter(annotation: dict | None, duration: float, fontfile: str) -> str:
    if not annotation:
        return ""
    x = int(annotation.get("x", 80))
    y = int(annotation.get("y", 320))
    w = int(annotation.get("width", 480))
    h = int(annotation.get("height", 180))
    label = _filter_text(str(annotation.get("label", "重点功能")))
    visible = f"between(t,0.35,{max(0.5, duration - 0.2):.3f})"
    font = _filter_text(fontfile)
    label_width = max(170, min(520, int(visual_units(str(annotation.get("label", "重点功能"))) * 30 + 54)))
    filters = [
        # Keep the evidence itself untouched: emphasis is border-only.
        f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0xFACC15@0.98:t=7:enable='{visible}'",
        f"drawbox=x={x}:y={max(20, y-62)}:w={label_width}:h=50:color=0x111827@0.92:t=fill:enable='{visible}'",
        f"drawtext=fontfile='{font}':text='{label}':x={x+18}:y={max(26, y-54)}:fontsize=30:fontcolor=white:enable='{visible}'",
    ]
    click = annotation.get("click")
    if isinstance(click, list) and len(click) == 2:
        cx, cy = int(click[0]), int(click[1])
        filters.extend([
            f"drawbox=x={cx-24}:y={cy-24}:w=48:h=48:color=white@0.95:t=5:enable='between(t,0.70,1.45)'",
            f"drawbox=x={cx-10}:y={cy-10}:w=20:h=20:color=0x2563EB@0.95:t=fill:enable='between(t,0.70,1.45)'",
        ])
    return ",".join(filters)


def is_cta_scene(scene: dict) -> bool:
    return scene.get("scene_type") == "cta" or scene.get("layout_variant") == "cta_background"


def write_ass(path: Path, scenes: list[dict], width: int, height: int) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Hiragino Sans GB,50,&H00FFFFFF,&H000000FF,&H00101828,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,90,90,265,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    rows = []
    for scene in scenes:
        start = float(scene["start"])
        end = start + float(scene["duration"])
        subtitle = wrap_subtitle(scene.get("subtitle") or scene["narration"])
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{ass_escape(subtitle)}")
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--storyboard", type=Path, required=True)
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--fonts-dir", type=Path, help="Directory containing a Chinese-capable font")
    p.add_argument("--keep-work", action="store_true")
    args = p.parse_args()

    ffmpeg = binary("FFMPEG_BIN", "ffmpeg")
    ffprobe = binary("FFPROBE_BIN", "ffprobe")
    board = json.loads(args.storyboard.read_text(encoding="utf-8"))
    canvas = board.get("canvas", {})
    width, height, fps = int(canvas.get("width", 1080)), int(canvas.get("height", 1920)), int(canvas.get("fps", 30))
    scenes = board.get("scenes", [])
    if not scenes:
        raise SystemExit("storyboard has no scenes")
    audio_duration = probe_duration(ffprobe, args.audio)
    board_duration = sum(float(s["duration"]) for s in scenes)
    scale = audio_duration / board_duration if board_duration else 1
    start = 0.0
    for scene in scenes:
        scene["duration"] = max(0.2, float(scene["duration"]) * scale)
        scene["start"] = start
        start += scene["duration"]

    work_obj = tempfile.TemporaryDirectory(prefix="ai-product-video-")
    work = Path(work_obj.name)
    annotation_font = "/System/Library/Fonts/Hiragino Sans GB.ttc"
    if args.fonts_dir and (args.fonts_dir / "Hiragino Sans GB.ttc").exists():
        annotation_font = str((args.fonts_dir / "Hiragino Sans GB.ttc").resolve())
    clips = []
    for i, scene in enumerate(scenes):
        clip = work / f"scene-{i:03d}.mp4"
        if is_cta_scene(scene):
            background_color = str(scene.get("background_color") or "0xF5F7FB")
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c={background_color}:s={width}x{height}:r={fps}",
                "-t", f"{scene['duration']:.3f}", "-an", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(clip),
            ], check=True)
            clips.append(clip)
            continue
        image = Path(scene["image"])
        if not image.is_absolute():
            image = (args.storyboard.parent / image).resolve()
        if not image.exists():
            raise SystemExit(f"missing scene image: {image}")
        frames = max(1, round(float(scene["duration"]) * fps))
        motion = str(scene.get("motion") or "push_in")
        layout_variant = str(scene.get("layout_variant") or "full_page_establishing")
        annotation = scene.get("annotation") or {}
        foreground = build_foreground_filter(motion, annotation.get("source_region"), width, height)
        layout_y = int(scene.get("layout_y", 240 if motion != "focus_crop" else 210))
        annotations = build_annotation_filter(annotation, float(scene["duration"]), annotation_font)
        movement = build_motion_filter(motion, frames, width, height)
        if annotations:
            final_chain = f"[{i}m];[{i}m]{annotations},format=yuv420p"
        else:
            final_chain = ",format=yuv420p"
        background = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=28[bg];"
        if layout_variant == "inset_zoom":
            region = annotation.get("source_region")
            if not region:
                raise ValueError("inset_zoom requires annotation.source_region")
            filter_graph = (
                background
                + build_inset_zoom_filter(region, width, height)
                + "[bg][context]overlay=(W-w)/2:170[context_base];"
                + f"[context_base][detail]overlay=130:610,{movement}{final_chain}"
            )
        else:
            filter_graph = (
                background
                + f"[0:v]{foreground}[fg];"
                + f"[bg][fg]overlay=(W-w)/2:{layout_y},{movement}{final_chain}"
            )
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(image), "-filter_complex", filter_graph, "-t", f"{scene['duration']:.3f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(clip)], check=True)
        clips.append(clip)

    concat = work / "concat.txt"
    concat_rows = []
    for clip_path in clips:
        escaped_path = str(clip_path).replace("'", "'\\''")
        concat_rows.append(f"file '{escaped_path}'\n")
    concat.write_text("".join(concat_rows), encoding="utf-8")
    silent = work / "silent.mp4"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent)], check=True)
    subtitles = work / "subtitles.ass"
    write_ass(subtitles, scenes, width, height)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    escaped_ass = str(subtitles).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    fonts_dir = args.fonts_dir
    if fonts_dir is None:
        for candidate in (Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"):
            if candidate.exists():
                fonts_dir = candidate
                break
    subtitle_filter = f"subtitles='{escaped_ass}'"
    if fonts_dir:
        escaped_fonts = str(fonts_dir.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        subtitle_filter += f":fontsdir='{escaped_fonts}'"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(args.audio), "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(args.output)], check=True)
    if args.keep_work:
        kept = args.output.parent / f"{args.output.stem}-render-work"
        shutil.copytree(work, kept, dirs_exist_ok=True)
        print(f"Render work kept: {kept}")
    work_obj.cleanup()
    print(f"Rendered {audio_duration:.2f}s {width}x{height} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
