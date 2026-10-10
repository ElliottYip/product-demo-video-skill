# Screenshot and evidence rules

## Source priority

For each product capture, in order: official homepage/logo and positioning; feature page matching the claim; actual UI or official demo; pricing only when narrated; official help docs or changelog. Use search results only to locate official pages, never as final rendered evidence.

The screenshot must prove the adjacent narration. A visually attractive but unrelated page is not usable evidence.

After capture, inspect the raster image itself. Approve it only when the decisive evidence is visibly present, matches the full claim rather than one fragment, is readable at phone size, has no cookie/chat/ad obstruction, contains no private data, and is current enough for the narration. Record this decision in `screenshot-reviews.json`; DOM text, URL correctness, and capture success alone are insufficient.

## Pre-capture checklist

- Verify the registered domain or official organization ownership.
- Match visible content to the exact claim and note any inference.
- Re-check prices, plan names, availability, and page date.
- Avoid login walls when a public source can prove the same point.
- Remove or mask names, emails, tokens, workspace data, billing data, and account identifiers.
- Dismiss cookie banners, newsletter dialogs, chat widgets, and ads without accepting unnecessary tracking.
- Wait for fonts, images, and lazy content to settle.
- Ensure the decisive words remain readable after 9:16 layout and phone-size playback.

## Capture modes

- Screenshot: default for stable homepage, feature, pricing, docs, and search evidence.
- Focused crop: preferred when the key element is small inside a wide desktop page.
- Scroll recording: use for a long sequence where movement proves navigation or connected information.
- Real operation: use when the narration describes an interaction or output that a static page cannot prove. Never fabricate clicks or results.

Start with a desktop viewport around 1440×1000. Record the full-page original when practical, then create a focused crop. Do not stretch screenshots to 9:16. Place a readable fitted foreground over a restrained blurred or solid background.

## Motion and annotation

Use slow push-ins, pans, crops, highlight boxes, arrows, click rings, keyword labels, and short scrolls only to direct attention. A highlight box must tightly frame the exact control or text that proves the current claim, not the surrounding card or arbitrary attractive region. Use a thick, high-contrast border with a fully transparent interior; never tint, recolor, or cover the evidence. Annotations must not imitate product UI. Keep branding and source identity visible when useful.

## Provenance

For every capture save: stable capture ID, product, URL, canonical URL if known, page title, publisher/domain, accessed-at timestamp with timezone, evidence type, mapped narration/claim, screenshot file, crop/scroll details, and verification notes. Redirected/final URL is authoritative.
