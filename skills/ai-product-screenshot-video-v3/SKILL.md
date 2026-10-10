---
name: ai-product-screenshot-video-v3
description: Create verified Chinese 9:16 AI-product information-feed videos that combine official product screenshots with selectable kinetic editorial styles. Use for AI tool recommendations, comparisons, listicles, feature explainers, or when a reference video should influence pacing and motion language without copying its branding. Preserves stable, axis-aligned evidence screenshots; supports a single continuous KIE Gemini TTS master, phrase-level subtitles, FOMO hook, CTA, and HyperFrames rendering.
---

# AI Product Screenshot Video V3

Build a fast, evidence-led short video in which official screenshots prove the narration while typography, cards, captions, particles, and transitions provide motion. Treat screenshots as factual exhibits, not decorative B-roll.

## Non-negotiable contract

- Keep screenshots upright, axis-aligned, sharp, and completely static. Never animate an image, crop container, evidence border, or proof label with translate, scale, rotate, skew, shake, flash, pulse, or opacity.
- Animate editorial layers around the proof: title characters, ordinal, feature cards, takeaway, caption card, particles, and scene transitions.
- The screenshot shown at each sentence must directly support that sentence. Reject mismatched or ambiguous evidence during multimodal review.
- Use one continuous KIE TTS generation for the main narration. Cut or align this master recording after generation; do not synthesize each sentence separately.
- Use the same speaker, `voice_name`, voice profile, style, pace, accent, scene, sample context, and temperature for the whole video.
- Keep subtitles inside portrait safe areas and derive their timing from the actual master audio.
- Add a three-second CTA tail by default. Its visual is a background/editorial end card, not another product proof screenshot.
- Do not copy a reference video's watermark, account name, platform UI, logos, exact trade dress, music, or frame-for-frame sequence.

## Inputs

Accept a full Chinese script, a product plus topic, multiple products, or a style-reference video. Also accept duration, platform, canvas, voice preference, whether to show pricing, whether to capture real operation, output directory, and `style_preset`.

If the user supplies only a product/topic, research before writing. Do not invent features, prices, reviews, rankings, user counts, or model behavior.

## Select a style

If the user specifies a style, honor it. Otherwise infer one from content, platform, desired pace, brand appearance, and audience; report the selected preset before rendering. Run `python3 scripts/list_styles.py` to display choices and read [style-presets.md](references/style-presets.md) for the full distinctions.

Available presets:

- `kinetic-dark`: dark kinetic technology; closest to a fast listicle grammar.
- `clean-editorial`: bright editorial magazine; suitable for Xiaohongshu and clear tutorials.
- `brand-adaptive`: derive a restrained palette from the product brand while retaining proof readability.
- `premium-tech`: minimal high-end technology; suitable for B2B, model, and developer products.
- `viral-neon`: highest-impact hook and kinetic typography; use sparingly for viral pacing.
- `evidence-first`: largest evidence area and least decoration; suitable for reviews and comparisons.

The user may also override theme tokens through `storyboard.theme`. Never let a custom theme reduce text contrast or recolor screenshot pixels.

## Workflow

### 1. Research and script

Search multiple official sources in this order: launch/release page, interactive comparison charts and downloadable official media, product/feature page, pricing page when price is mentioned, documentation, help center, changelog, and official demo. A documentation page may verify a claim but must not automatically become the main visual when the launch page provides a clearer chart, comparison, UI demo, or downloadable asset. Use trustworthy search results only as navigation or supplemental evidence. Save URL, title, access time, claim, source type, and asset origin in `sources.json`.

Write for short-video retention:

- 0–3 seconds: concrete hook with curiosity, consequence, or FOMO; no false claims.
- Middle: one claim per spoken phrase, escalating value, comparison, or consequence.
- Ending: concise resolution and natural CTA.
- Prefer short spoken sentences, natural Mandarin, readable English product names, and verbalized numbers.

Read [research-and-visual-qa.md](references/research-and-visual-qa.md) and [screenshot-rules.md](references/screenshot-rules.md).

### 2. Capture and review evidence

Use `scripts/capture_pages.py` or a real browser. Close cookie and chat overlays. Inspect tab sets, carousels, embedded videos, Vega/SVG charts, download buttons, before/after examples, and media galleries instead of capturing only the visible article text. Capture enough surrounding page context to identify the official source, plus an exact focus crop for the narrated claim.

For every product, build a visual inventory before storyboarding. Prefer at least three visually distinct official evidence types when available, such as a release-page hero, comparison chart, product interface, downloadable example, pricing card, or docs excerpt. Never add an attractive asset when it proves a different claim.

Run multimodal review before editing. Confirm official identity, claim match, freshness, readable mobile crop, no private data, no login wall, and no overlays. Record the normalized `source_region`; never guess a coordinate from layout alone.

### 3. Plan hybrid scenes

Create `storyboard.json` using [v3-storyboard-schema.md](references/v3-storyboard-schema.md). Every proof scene may define:

- `kinetic.title`, `tagline`, `ordinal`, and `badge`
- two to four concise `features`
- a single `takeaway`
- `highlight_terms` for phrase-level caption emphasis
- `layout`: `center-proof`, `split-proof`, `focus-stage`, or `proof-poster`
- `show_evidence`

Do not repeat one layout for every scene. Rotate layouts only when the evidence remains readable. Read [hybrid-motion-language.md](references/hybrid-motion-language.md).

### 4. Generate one continuous voice master

Read [kie-gemini-tts.md](references/kie-gemini-tts.md) before calling the API. Use `KIE_API_KEY` from the environment and never write it to disk or logs.

Generate a short voice audition on first use, then a single dialogue turn for the whole narration. Use punctuation and brief written pauses between sentences. Run `scripts/align_continuous_tts.py` to derive sentence boundaries and preserve small natural gaps. Store the final configuration in `tts-config.json` without the key.

### 5. Build the v3 HyperFrames project

Use the dedicated hybrid builder:

```bash
python3 scripts/build_hybrid_hyperframes_project.py \
  --storyboard /absolute/path/storyboard.json \
  --audio /absolute/path/narration.wav \
  --output-project /absolute/path/hyperframes-project \
  --style kinetic-dark
```

Use `--style auto` to read `style_preset` from the storyboard. The builder creates a static context screenshot and a static focus crop for each evidence scene; its GSAP timeline intentionally excludes every proof-layer selector.

Run the HyperFrames workflow described in [hyperframes-rendering.md](references/hyperframes-rendering.md): validate, check at several timestamps, inspect snapshots, render, then validate the MP4.

### 6. Visual QA and delivery

Inspect the hook, every scene boundary, each focus crop, long subtitle frames, and CTA. Reject the render if:

- any screenshot tilts, drifts, zooms, flickers, changes color, or flashes;
- an evidence frame supports a different sentence;
- a highlight box surrounds the wrong control;
- captions leave the safe region or cover decisive evidence;
- spoken phrases and subtitles visibly disagree;
- style variety harms consistency or proof readability.

Run `scripts/validate_hyperframes_project.py`, HyperFrames `check`, and `scripts/validate_output.py`. Do not claim completion until `final.mp4` plays successfully.

## Output contract

Preserve at least:

```text
narration.txt
storyboard.json
style-config.json
sources.json
tts-config.json
screenshots/
audio/
hyperframes-project/
preview-snapshots/
final.mp4
```

Also return the screenshots used, selected style and reason, voice and all non-secret TTS parameters, validation result, and video duration. Read [output-schema.md](references/output-schema.md) for inherited fields.

## Scripts

- `research_product.py`: normalize and validate research records.
- `capture_pages.py`: browser evidence capture helper.
- `plan_storyboard.py`: initial scene planning.
- `apply_media_overrides.py`: merge reviewed launch-page assets into an existing storyboard without changing timing.
- `generate_tts.py`: current KIE continuous TTS task creation and download.
- `align_continuous_tts.py`: align phrases to the single voice master.
- `analyze_reference_video.py`: inspect a style reference without copying it.
- `build_hybrid_hyperframes_project.py`: v3 screenshot-plus-kinetic builder.
- `list_styles.py`: list selectable style presets.
- `validate_hyperframes_project.py`: static-project checks.
- `validate_output.py`: rendered-media validation.
- `test_hybrid_builder.py`: regression test ensuring proof media stays static.
