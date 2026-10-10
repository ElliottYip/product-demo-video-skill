# Voice selection and Chinese audition

## Automatic selection

Score candidates against content, audience, requested gender tendency, expertise, emotion, pace, product category, platform, and the account's saved series profile. Do not ask for a voice when a reasonable automatic choice exists.

Default ranking for AI-product recommendation:

1. Achird — friendly, natural, general recommendations.
2. Charon — tutorials and explanatory content.
3. Sadaltager — professional reviews and productivity tools.
4. Puck — younger, faster feed videos.
5. Sulafat — warm, lifestyle-oriented recommendations.
6. Gacrux — mature, trusted business tools.
7. Kore — conclusions, comparisons, and firm judgment.

Suggested profiles:

- General recommendation: Achird, `Vocal Smile`, `Natural`, `Neutral`, temperature 0.9–1.0.
- Tutorial: Charon, `Deadpan`, `Natural`, `Neutral`, 0.75–0.95.
- Professional review: Sadaltager, `Deadpan`, `Natural`, `Neutral`, 0.75–0.9.
- Youthful fast feed: Puck, `Vocal Smile`, `Natural`, `Neutral`, 0.95–1.1, then apply the default `1.08×` post-process tempo; use `Rapid Fire` only after a Chinese audition proves it remains clear.
- Warm lifestyle: Sulafat, `Empathetic`, `Natural`, `Neutral`, 0.85–1.0.
- Business: Gacrux, `Deadpan`, `Natural`, `Neutral`, 0.75–0.9.
- Firm comparison: Kore, `Deadpan`, `Staccato` only if audition remains natural; otherwise `Natural`.

For Mandarin, do not select an English accent option by default. `audio_profile`, `scene`, and `sample_context` carry most high-level direction. Pace is a categorical performance mode, not an exact speed multiplier. Keep `Natural` as the normal provider pace and use the deterministic post-process tempo for modest speed changes.

## Default Mandarin direction

Use this intent, adapted to the specific video:

> 自然、聪明、熟悉 AI 产品的中文内容创作者；口语化，有轻微兴奋感，但不使用传统广告播音腔；开头有抓力，中段清楚可信，结尾简洁。

Preprocess text so English product names, numbers, abbreviations, URLs, units, and punctuation are speakable. Prefer Chinese punctuation and semantic sentence splits. Avoid overloading inline tags.

## First-use audition gate

Generate 10–15 seconds that contains:

- ordinary Mandarin;
- the exact English product name;
- at least one number, price, date, or abbreviation that appears in the script;
- a hook and an explanatory clause.

Inspect duration, peak/clipping, silence, speaking rate, segmentation, intelligibility, product-name pronunciation, numerical pronunciation, emotional fit, and mechanical artifacts. Use waveform measurements plus human listening. If any critical item fails, revise pronunciation/segmentation once, then move to the next ranked voice.

Store a reusable series profile without secrets:

```json
{
  "series_id": "account-name",
  "voice_name": "Achird",
  "audio_profile": "Friendly natural Mandarin AI-tool creator",
  "style": "Vocal Smile",
  "pace": "Natural",
  "accent": "Neutral",
  "temperature": 0.9,
  "audition_passed_at": "ISO-8601 timestamp",
  "audition_notes": "Clear Mandarin; English name and numbers accepted."
}
```
