# Hyperframes rendering contract

Verified against the official `heygen-com/hyperframes` repository and documentation on 2026-07-21. The tested CLI version is `0.7.65`.

Official sources:

- https://github.com/heygen-com/hyperframes
- https://hyperframes.heygen.com/quickstart
- https://hyperframes.heygen.com/guides/rendering

## Why V2 differs from V1

V1 renders still images with FFmpeg filters. V2 writes an editable HTML composition and lets Hyperframes seek the timeline frame by frame in headless Chrome before encoding with FFmpeg. This enables independently animated screenshot context, exact crop panels, labels, borders, caption cards, transitions, and reusable layout components.

## Composition requirements

- Use Node.js 22 or newer and FFmpeg.
- Root element: `data-composition-id`, `data-start`, `data-width`, `data-height`, `data-duration`, and explicit CSS width/height.
- Every visible timed element is a direct child of the root, has a unique id, `class="clip"`, `data-start`, `data-duration`, and `data-track-index`.
- Audio is a direct child of the root. Do not wrap it.
- Create exactly one synchronous `gsap.timeline({paused:true})` and register it at `window.__timelines["main"]`.
- Keep media local. Do not fetch screenshots or narration at render time.
- Use deterministic finite motion. Do not use `Date.now`, `performance.now`, unseeded `Math.random`, input events, asynchronous timeline construction, or infinite repeat.
- Animate transform aliases, opacity, color, background color, border color, or border radius. Do not tween width, height, top, left, margin, padding, display, or raw visibility.
- Never animate scale, rotation, or fractional translation on a card that contains a screenshot. Chromium resamples the raster on every frame and produces visible shake. Keep the context crop, focus crop, evidence border, and evidence label static; put motion on titles and caption cards instead.
- Never reveal an evidence border with opacity, scale, stroke-dash, or repeating animation. The box must be correct and fully visible from the first frame of its scene, with an unchanged transparent interior.
- A crop is approved only when its pixels directly prove that sentence. Feature scenes and price scenes from the same page must use different `source_region` values when the evidence is in different page areas.

## CLI gates

```bash
npx --yes hyperframes@0.7.65 check <project> --snapshots
npx --yes hyperframes@0.7.65 preview <project>
npx --yes hyperframes@0.7.65 render <project> --quality high --output final.mp4
```

Run `check` before preview. Inspect snapshots at scene midpoints. Render only after approval, except a clearly identified local draft render used to validate the skill implementation.

## Audio ownership

Do not invoke Hyperframes/HeyGen/Kokoro narration generation in this skill. KIE owns narration. Hyperframes only receives the finished local `narration.wav` and renders it on the composition timeline.

For sentence-locked sync, generate the entire narration in one KIE task and one dialogue turn. Detect and review sentence-ending silence boundaries, derive scene/subtitle durations from those cuts, and export sentence WAVs only as edit references. Mount the continuous PCM master as the single `<audio>` in the final Hyperframes composition; never concatenate the edit cuts back together. This preserves one continuous voice performance and avoids both per-request timbre drift and per-clip encoder padding. Keep per-sentence KIE generation only as an explicit fallback.
