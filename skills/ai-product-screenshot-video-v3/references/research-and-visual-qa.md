# Official research and visual QA

## Official source matrix

For each product, gather at least four records across at least three distinct official pages:

- positioning: official homepage or product landing page;
- feature: official page that explicitly supports the narrated capability;
- product proof: actual product UI, official interactive demo, or official demo media;
- operational proof: official docs, help center, API reference, changelog, or release note;
- commercial proof: official pricing page whenever the script mentions price, plan, credits, quota, trial, or discount.

Verify ownership through the registered product domain, navigation links from that domain, an official documentation subdomain, or an official repository/organization linked by the product. Record the basis. Multiple crops from one long page may provide different shots, but do not count as distinct source pages.

Search-result snippets, AI summaries, third-party reviews, affiliate pages, unofficial GitHub mirrors, and copied documentation are discovery aids only. Do not render them as evidence when the user requires official sources.

## Claim triangulation

Map every factual sentence to at least one direct official source. For volatile or consequential claims—price, limits, availability, model names, plan inclusions, or release status—cross-check a second official surface such as pricing plus docs or product page plus changelog. If official surfaces disagree, use the newest dated source, qualify the narration, and record the conflict.

## Multimodal screenshot review

After capture, inspect the actual raster screenshot at original resolution and phone-scale preview. Do not approve based only on URL, page title, DOM text, OCR, or successful file creation.

For every screenshot confirm:

- the exact decisive words, control, state, price, or demo result are visible;
- the image proves the entire adjacent narration, not one convenient fragment;
- the evidence stays readable after 9:16 placement or planned magnification;
- cookie banners, chat widgets, ads, sticky headers, and loading skeletons do not obstruct it;
- there is no email, name, token, workspace, billing, or account data;
- the crop preserves enough page identity to establish provenance;
- the annotation target can be placed tightly without inventing or recoloring evidence.

Write the result to `screenshot-reviews.json`. Reject and recapture any failed item. Plan scenes only from approved source IDs.
