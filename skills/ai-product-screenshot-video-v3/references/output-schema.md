# Output schemas

All JSON is UTF-8, two-space indented, and must not contain API keys.

## narration.txt and subtitles.srt

After TTS finishes, generate both files from the same sentence timeline with `scripts/align_timeline.py`. `narration.txt` uses one sentence per line:

```text
[00:00.000 --> 00:04.280 | 4.280秒] 第一句旁白。
[00:04.280 --> 00:08.950 | 4.670秒] 第二句旁白。
```

`subtitles.srt` must contain identical sentence boundaries. Scene `start`, `end`, and `duration` in `storyboard.json` are the machine-readable source of truth after alignment. Boundaries must be contiguous, non-overlapping, and end at the finished narration audio duration.

## sources.json

```json
{
  "schema_version": "1.0",
  "generated_at": "ISO-8601",
  "products": ["Product"],
  "sources": [{
    "id": "src-001",
    "product": "Product",
    "url": "https://official.example/feature",
    "final_url": "https://official.example/feature",
    "title": "Feature title",
    "publisher": "Official Product",
    "accessed_at": "ISO-8601",
    "evidence_type": "official_feature",
    "official": true,
    "official_basis": "registered product domain",
    "claim": "Verifiable claim",
    "narration": "Mapped narration",
    "screenshot": "screenshots/src-001.png",
    "capture_mode": "screenshot",
    "verification_notes": "Why it proves the claim"
  }]
}
```

`sources.json.research_policy` records the official-only minimums and whether multimodal screenshot review is mandatory.

## screenshot-reviews.json

Create this only after visually inspecting each captured image:

```json
{
  "schema_version": "1.0",
  "reviews": [{
    "source_id": "src-001",
    "status": "approved",
    "review_method": "multimodal_image_inspection",
    "evidence_visible": true,
    "claim_match": true,
    "readable_mobile": true,
    "overlays_clear": true,
    "privacy_safe": true,
    "visible_evidence": "Feature control and its label are both visible in the crop.",
    "reviewed_at": "ISO-8601",
    "notes": ""
  }]
}
```

Use `status: rejected` and record the failure when any boolean check is false. Never reference a rejected or unreviewed source from `storyboard.json`.

## storyboard.json

```json
{
  "schema_version": "1.0",
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "target_duration": 30,
  "scenes": [{
    "id": "scene-001",
    "start": 0.0,
    "end": 4.2,
    "duration": 4.2,
    "narration": "一句中文旁白。",
    "subtitle": "一句中文旁白。",
    "source_id": "src-001",
    "image": "screenshots/src-001.png",
    "motion": "focus_crop",
    "layout_variant": "inset_zoom",
    "layout_y": 180,
    "annotation": {
      "type": "feature",
      "source_region": {"x": 0.02, "y": 0.48, "width": 0.50, "height": 0.50},
      "x": 125,
      "y": 605,
      "width": 830,
      "height": 550,
      "label": "1–2 人 · 30 个声音",
      "click": [890, 720]
    },
    "claim_status": "verified"
  }]
}
```

Scene paths are relative to the storyboard file. `start` and `duration` are seconds. Allowed motion names: `push_in`, `pan_left`, `pan_right`, `focus_crop`, `static`, `scroll`. Use normalized 0–1 coordinates for `source_region`; annotation box and click coordinates are absolute canvas pixels. Recommended layout variants: `full_page_establishing`, `inset_zoom`, `feature_closeup`, `documentation_focus`, and `editorial_evidence`. `claim_status` is `verified`, `qualified`, or `blocked`; do not render a blocked claim as factual narration.

Append this scene by default after all evidence scenes:

```json
{
  "id": "scene-cta",
  "scene_type": "cta",
  "duration": 3.0,
  "fixed_duration": 3.0,
  "narration": "想看更多实用 AI 工具，记得关注账号。",
  "subtitle": "想看更多实用 AI 工具，记得关注账号。",
  "source_id": null,
  "image": null,
  "motion": "static",
  "layout_variant": "cta_background",
  "background_color": "0xF5F7FB",
  "annotation": null,
  "claim_status": "not_applicable"
}
```

The CTA is the only scene with no source evidence. Keep it last, preserve exactly three seconds during audio alignment, and render only the plain background plus synchronized subtitle while its CTA voice plays.

## tts-config.json

```json
{
  "schema_version": "1.0",
  "model": "google/gemini-3-1-flash-tts",
  "selection_reason": "Friendly general AI tool recommendation",
  "postprocess": {"tempo": 1.08, "profile": "fast_information_feed"},
  "series_id": null,
  "input": {
    "speakers": [{
      "speaker_id": "Speaker 1",
      "voice_name": "Achird",
      "audio_profile": "Friendly natural Mandarin AI-tool creator",
      "style": "Vocal Smile",
      "pace": "Natural",
      "accent": "Neutral"
    }],
    "dialogue_turns": [{"speaker_id": "Speaker 1", "text": "旁白。"}],
    "temperature": 0.9,
    "scene": "Chinese technology creator recording in a clean home studio.",
    "sample_context": "Natural Mandarin, clear and conversational, not a broadcast advertisement."
  },
  "audition": {"required": true, "text": "试听文本", "status": "pending"}
}
```

`selection_reason`, `series_id`, `audition`, and `postprocess` are local metadata and are not sent to KIE. The API payload contains only `model`, optional `callBackUrl`, and `input`. Default `postprocess.tempo` is `1.08`; `audio/task.json` must record the actual value used.
