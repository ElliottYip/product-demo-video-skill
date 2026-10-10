# Product Demo Video Skill

Create vertical product explainers from official screenshots, narration and motion design. Product evidence stays readable while titles, captions and transitions give the story its pace.

[中文](README.md) · **English**

Maintained and refined by Yilun Ye through practical project work. Existing source notices and licenses remain attached to the relevant material; see [NOTICE](NOTICE.md).

## What it covers

- Match each claim to a screenshot and preserve its source.
- Align captions to one continuous narration master.
- Choose from six visual styles and several scene layouts.
- Keep storyboards, screenshots, voice configuration and previews with the render.

## Workflow

Research → Evidence review → Script → Narration → Motion layout → Review and export

## Get started

Install the dependencies below, then copy the skill folders. Back up existing skills with matching names, and keep suite members as siblings.

```bash
git clone https://github.com/ElliottYip/product-demo-video-skill.git
cd product-demo-video-skill
mkdir -p ~/.codex/skills
cp -R skills/* ~/.codex/skills/
```

Start a new session and try:

```text
Use $ai-product-screenshot-video-v3 to plan a 30-second vertical explainer from the product URL and screenshots I provide. Verify claims and sources before proposing the script and visual style.
```

## Requirements

Python 3.10+, Pillow and FFmpeg/ffprobe. Full rendering requires Node.js 22+ and npm/npx. Capture uses a Codex Playwright wrapper or host browser tools. KIE narration requires your own account.

[Configuration and checks](docs/USAGE.md)

## Included skills

- [ai-product-screenshot-video-v3](skills/ai-product-screenshot-video-v3/SKILL.md)

examples/ contains editable task briefs; docs/ records setup, validation and snapshot provenance.

## Current version

The current V3 entry builds on V1 screenshot cards and V2 HyperFrames compositions, adding hybrid layouts, style presets, continuous-narration alignment and evidence-stability checks. Supporting scripts remain included; older entry points are not duplicated.

[Packaging notes](CHANGELOG.md) · [Verification](docs/VERIFICATION.md)

## Scope

The default workflow targets Chinese 9:16 product explainers. Browser, speech and rendering dependencies must be configured separately; credentials are not included.
