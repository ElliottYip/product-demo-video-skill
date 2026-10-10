#!/usr/bin/env python3
"""Validate a KIE Gemini 3.1 Flash TTS config, submit/poll a task, and download audio."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREATE_URL = "https://api.kie.ai/api/v1/jobs/createTask"
QUERY_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"
MODEL = "google/gemini-3-1-flash-tts"
DEFAULT_TEMPO = 1.08
VOICES = {"Achernar","Achird","Algenib","Algieba","Alnilam","Aoede","Autonoe","Callirrhoe","Charon","Despina","Enceladus","Erinome","Fenrir","Gacrux","Iapetus","Kore","Laomedeia","Leda","Orus","Puck","Pulcherrima","Rasalgethi","Sadachbia","Sadaltager","Schedar","Sulafat","Umbriel","Vindemiatrix","Zephyr","Zubenelgenubi"}
STYLES = {"Vocal Smile","Newscaster","Whisper","Empathetic","Promo/Hype","Deadpan"}
PACES = {"Natural","Rapid Fire","The Drift","Staccato"}
ACCENTS = {"Neutral","American (Gen)","American (Valley)","American (South)","British (RP)","British (Brixton)","Transatlantic","Australian"}


def validate_tempo(value: float) -> float:
    tempo = float(value)
    if not 0.5 <= tempo <= 2.0:
        raise ValueError("tempo must be in FFmpeg atempo range [0.5, 2.0]")
    return tempo


def atempo_filter(value: float) -> str:
    return f"atempo={validate_tempo(value):.3f}"


def ensure_cta_turn(config: dict, storyboard: dict) -> bool:
    """Append the storyboard CTA to the primary voice once; return whether config changed."""
    cta = next((scene for scene in storyboard.get("scenes", []) if scene.get("scene_type") == "cta"), None)
    if not cta:
        return False
    text = str(cta.get("narration") or "").strip()
    inp = config.get("input") or {}
    turns = inp.get("dialogue_turns") or []
    if not text or any(
        str(turn.get("text") or "").strip() == text
        or str(turn.get("text") or "").strip().endswith(text)
        for turn in turns
    ):
        return False
    speakers = inp.get("speakers") or []
    if not speakers:
        raise ValueError("cannot add CTA before a primary speaker is configured")
    turns.append({"speaker_id": speakers[0]["speaker_id"], "text": text})
    inp["dialogue_turns"] = turns
    config["input"] = inp
    return True


def validate(config: dict) -> dict:
    if config.get("model") != MODEL:
        raise ValueError(f"model must be {MODEL}")
    inp = config.get("input")
    if not isinstance(inp, dict):
        raise ValueError("input object is required")
    speakers = inp.get("speakers")
    turns = inp.get("dialogue_turns")
    if not isinstance(speakers, list) or not 1 <= len(speakers) <= 2:
        raise ValueError("speakers must contain 1-2 items")
    ids = []
    for speaker in speakers:
        sid = speaker.get("speaker_id")
        if sid not in {"Speaker 1", "Speaker 2"} or sid in ids:
            raise ValueError("speaker_id must be unique Speaker 1 or Speaker 2")
        ids.append(sid)
        if speaker.get("voice_name") not in VOICES:
            raise ValueError(f"unknown voice_name: {speaker.get('voice_name')}")
        if len(str(speaker.get("audio_profile", ""))) > 300:
            raise ValueError("audio_profile exceeds 300 characters")
        if speaker.get("style", "Deadpan") not in STYLES:
            raise ValueError("invalid style; re-check current KIE schema")
        if speaker.get("pace", "Natural") not in PACES:
            raise ValueError("invalid pace; re-check current KIE schema")
        if speaker.get("accent", "Neutral") not in ACCENTS:
            raise ValueError("invalid accent; re-check current KIE schema")
    if not isinstance(turns, list) or not turns:
        raise ValueError("dialogue_turns must be a non-empty list")
    for turn in turns:
        if turn.get("speaker_id") not in ids or not str(turn.get("text", "")).strip():
            raise ValueError("every dialogue turn needs a known speaker_id and non-empty text")
    temp = float(inp.get("temperature", 1))
    if not 0 <= temp <= 2:
        raise ValueError("temperature must be in [0, 2]")
    for field in ("scene", "sample_context"):
        if len(str(inp.get(field, ""))) > 1000:
            raise ValueError(f"{field} exceeds 1000 characters")
    return {"model": MODEL, "input": inp}


def request_json(url: str, key: str, method: str = "GET", body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ai-product-screenshot-video/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        if exc.code in {400, 422}:
            raise RuntimeError(f"KIE schema validation failed ({exc.code}). Re-read the official live schema before retrying. {detail}") from exc
        raise RuntimeError(f"KIE HTTP {exc.code}: {detail}") from exc


def result_urls(record: dict) -> list[str]:
    data = record.get("data") or {}
    result = data.get("resultJson") or {}
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            result = {}
    urls = result.get("resultUrls") or result.get("result_urls") or []
    return [x for x in urls if isinstance(x, str) and x.startswith(("https://", "http://"))]


def convert_audio(src: Path, dst: Path, tempo: float = DEFAULT_TEMPO) -> None:
    tempo = validate_tempo(tempo)
    ffmpeg = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if not ffmpeg:
        if tempo == 1.0 and src.suffix.lower() == dst.suffix.lower():
            shutil.copy2(src, dst)
            return
        raise RuntimeError("ffmpeg is required to normalize or tempo-adjust downloaded audio")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vn"]
    if tempo != 1.0:
        command.extend(["-filter:a", atempo_filter(tempo)])
    command.extend(["-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(dst)])
    subprocess.run(command, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--storyboard", type=Path, help="Sync the default CTA scene into dialogue_turns before submission")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--task-record", type=Path, default=Path("audio/task.json"))
    p.add_argument("--callback-url")
    p.add_argument("--dry-run", action="store_true", help="Validate and print redacted payload without calling KIE")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--resume-task-id", help="Resume polling/downloading an existing task without creating a new one")
    p.add_argument("--tempo", type=float, default=DEFAULT_TEMPO, help="Post-process tempo; defaults to 1.08 for a brisk information-feed rhythm")
    p.add_argument("--continuous", action="store_true", help="Require one dialogue turn for a single continuous performance")
    args = p.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    tempo = validate_tempo(args.tempo)
    changed = False
    if args.storyboard:
        board = json.loads(args.storyboard.read_text(encoding="utf-8"))
        if ensure_cta_turn(config, board):
            changed = True
    postprocess = dict(config.get("postprocess") or {})
    expected_postprocess = {"tempo": tempo, "profile": "fast_information_feed" if tempo > 1 else "natural"}
    if any(postprocess.get(key) != value for key, value in expected_postprocess.items()):
        postprocess.update(expected_postprocess)
        config["postprocess"] = postprocess
        changed = True
    if changed:
        args.config.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = validate(config)
    if args.continuous and len(payload["input"]["dialogue_turns"]) != 1:
        raise ValueError("--continuous requires exactly one dialogue_turn containing the complete narration")
    if args.callback_url:
        payload["callBackUrl"] = args.callback_url
    print(f"Voice: {payload['input']['speakers'][0]['voice_name']}")
    print(f"Selection reason: {config.get('selection_reason', 'not recorded')}")
    print(f"Post-process tempo: {tempo:.2f}x")
    print(f"Generation mode: {'single continuous turn' if args.continuous else 'standard'}")
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    key = os.environ.get("KIE_API_KEY")
    if not key:
        raise SystemExit("KIE_API_KEY is not set; no request was sent")
    if args.resume_task_id:
        task_id = args.resume_task_id.strip()
        if not task_id:
            raise ValueError("--resume-task-id cannot be empty")
        print(f"Resuming task: {task_id}")
    else:
        created = request_json(CREATE_URL, key, method="POST", body=payload)
        task_id = str((created.get("data") or {}).get("taskId") or "")
        if not task_id:
            raise RuntimeError(f"KIE did not return taskId: {json.dumps(created, ensure_ascii=False)[:1000]}")
        print(f"Submitted task: {task_id}")
    args.task_record.parent.mkdir(parents=True, exist_ok=True)
    record_meta = {"task_id": task_id, "model": MODEL, "created_at": datetime.now(timezone.utc).isoformat(), "state": "submitted", "postprocess_tempo": tempo, "generation_mode": "single_continuous_turn" if args.continuous else "standard"}
    args.task_record.write_text(json.dumps(record_meta, indent=2) + "\n", encoding="utf-8")

    deadline = time.monotonic() + args.timeout
    delay = 2.5
    record = {}
    while time.monotonic() < deadline:
        time.sleep(delay)
        url = QUERY_URL + "?" + urllib.parse.urlencode({"taskId": task_id})
        record = request_json(url, key)
        data = record.get("data") or {}
        state = str(data.get("state", "")).lower()
        print(f"State: {state or 'unknown'}")
        record_meta.update({"state": state, "updated_at": datetime.now(timezone.utc).isoformat(), "fail_code": data.get("failCode"), "fail_message": data.get("failMsg")})
        args.task_record.write_text(json.dumps(record_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if state == "success":
            break
        if state == "fail":
            raise RuntimeError(f"KIE task failed: {data.get('failCode')} {data.get('failMsg')}")
        delay = min(10.0, delay * 1.35)
    else:
        raise TimeoutError(f"KIE task {task_id} exceeded {args.timeout}s")

    urls = result_urls(record)
    if not urls:
        raise RuntimeError("successful KIE task did not contain resultUrls")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".download")
    download_request = urllib.request.Request(urls[0], headers={
        "User-Agent": "Mozilla/5.0 (compatible; ai-product-screenshot-video/1.0)",
        "Accept": "audio/*,application/octet-stream;q=0.9,*/*;q=0.1",
    })
    with urllib.request.urlopen(download_request, timeout=120) as response, temporary.open("wb") as fh:
        shutil.copyfileobj(response, fh)
    convert_audio(temporary, args.output, tempo=tempo)
    temporary.unlink(missing_ok=True)
    print(f"Audio saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
