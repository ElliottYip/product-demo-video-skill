# V3 storyboard extension

V3 retains the v2 storyboard timing and evidence fields and adds optional style metadata.

```json
{
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "audio_duration": 27.4,
  "style_preset": "kinetic-dark",
  "theme": {
    "primary": "#8b5cf6",
    "secondary": "#f59e0b",
    "signal": "#14b8a6"
  },
  "scenes": [
    {
      "id": "scene-001",
      "start": 0.0,
      "duration": 2.8,
      "narration": "别再默认选最贵的模型。",
      "subtitle": "别再默认选最贵的模型",
      "image": "screenshots/model-selector.png",
      "annotation": {
        "label": "模型选择器",
        "source_region": {"x": 0.18, "y": 0.22, "width": 0.61, "height": 0.31}
      },
      "kinetic": {
        "ordinal": "01",
        "badge": "官方界面 · 已核实",
        "title": "别选最贵",
        "tagline": "任务不同，最佳档位也不同",
        "features": ["快：高频日常任务", "省：批量与低成本任务"],
        "takeaway": "先看任务，再选模型",
        "highlight_terms": ["最贵", "任务"],
        "layout": "focus-stage",
        "show_evidence": true
      }
    }
  ]
}
```

Allowed `style_preset` values are listed in `style-presets.md`. Theme overrides accept existing string tokens only; unknown keys are ignored.

Allowed `layout` values:

- `center-proof`
- `split-proof`
- `focus-stage`
- `proof-poster`

Keep feature strings short enough for two-column portrait cards. When a narration phrase needs more than four points, split it into another scene.
