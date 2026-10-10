# KIE Gemini 3.1 Flash TTS — verified API reference

Verified 2026-07-21 against KIE's official live product page and unified task documentation:

- Product/schema: https://kie.ai/gemini-3.1-flash-tts
- Unified task query: https://docs.kie.ai/market/common/get-task-detail
- API root: https://api.kie.ai

The product page is the current model-specific schema source. The documentation page describes the shared task lifecycle. Re-check both before implementation when the live page changes, and after any 400/422 validation error.

## Authentication and endpoints

Use `Authorization: Bearer <KIE_API_KEY>` and `Content-Type: application/json`. Read the secret only from environment variable `KIE_API_KEY`; never put it in code, JSON output, shell history, logs, or a URL.

Create:

```http
POST https://api.kie.ai/api/v1/jobs/createTask
```

Query:

```http
GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId=<url-encoded-task-id>
```

Create body:

```json
{
  "model": "google/gemini-3-1-flash-tts",
  "callBackUrl": "https://optional-public-endpoint.example/callback",
  "input": {
    "speakers": [{
      "speaker_id": "Speaker 1",
      "voice_name": "Achird",
      "audio_profile": "Friendly Chinese AI-product creator",
      "style": "Vocal Smile",
      "pace": "Natural",
      "accent": "Neutral"
    }],
    "dialogue_turns": [{"speaker_id": "Speaker 1", "text": "你好。"}],
    "temperature": 1,
    "scene": "A clean home studio for a Chinese technology short video.",
    "sample_context": "Natural Mandarin, conversational, clear, lightly excited, not a broadcast advertisement."
  }
}
```

`callBackUrl` is optional. The key spelling is intentionally camel-cased exactly as shown.

## Current input constraints

`speakers` is required, 1–2 items, with unique `speaker_id`. Each item:

- `speaker_id`: required; current UI options `Speaker 1` or `Speaker 2`; must match dialogue turns.
- `voice_name`: required; one of the 30 built-ins below.
- `audio_profile`: optional text, maximum 300 characters.
- `style`: optional enum; `Vocal Smile`, `Newscaster`, `Whisper`, `Empathetic`, `Promo/Hype`, `Deadpan`. Current default: `Deadpan`.
- `pace`: optional enum; `Natural`, `Rapid Fire`, `The Drift`, `Staccato`. Current default: `Natural`.
- `accent`: optional enum; `Neutral`, `American (Gen)`, `American (Valley)`, `American (South)`, `British (RP)`, `British (Brixton)`, `Transatlantic`, `Australian`. Use `Neutral` for Mandarin unless a tested profile proves otherwise.

`dialogue_turns` is required with at least one item. Each item has a required `speaker_id` that exists in `speakers`, plus non-empty `text`. Text supports inline audio tags such as `[shouting]`, `[whispers]`, and `[urgency]`; use tags sparingly.

`temperature` is optional, number 0–2 inclusive, step 0.01, default 1. `scene` and `sample_context` are optional strings, each up to 1000 characters.

## Task lifecycle and result

A successful create response is normally:

```json
{"code": 200, "msg": "success", "data": {"taskId": "..."}}
```

Poll the record endpoint with exponential backoff starting around 2–3 seconds. Official states are `waiting`, `queuing`, `generating`, `success`, and `fail`. Query no faster than 10 requests/second; normal polling is every 2–5 seconds with a 10–15 minute ceiling.

On success, `data.resultJson` is a JSON-encoded string, commonly `{"resultUrls":["https://..."]}`. Parse it, download the first audio URL immediately, and convert to the local editing format. Generated URLs commonly expire after 24 hours. On failure use `failCode` and `failMsg`; do not blindly retry invalid input.

The generic Market docs recommend callback delivery for production. The exact model-specific callback body is not published on the live Gemini 3.1 Flash TTS page as of verification. Therefore treat callback payloads as untrusted/versioned: require JSON POST, match `taskId`, accept `state/resultJson` or `data.info.resultUrls` variants, make handling idempotent, and fall back to the official record query endpoint before consuming a result.

## Built-in voices

The live schema contains exactly these 30 identifiers. Descriptions below are selection guidance supplied for this skill; verify Chinese behavior by audition rather than assuming the English descriptor predicts Mandarin quality.

| Voice | Intended quality |
|---|---|
| Zephyr | 明亮 |
| Puck | 活泼、积极 |
| Charon | 知识讲解、信息型 |
| Kore | 坚定 |
| Fenrir | 兴奋、有冲劲 |
| Leda | 年轻 |
| Orus | 坚定、直接 |
| Aoede | 轻松、轻快 |
| Callirrhoe | 随和 |
| Autonoe | 明亮 |
| Enceladus | 气声感 |
| Iapetus | 清晰 |
| Umbriel | 轻松随和 |
| Algieba | 顺滑 |
| Despina | 顺滑 |
| Erinome | 清晰 |
| Algenib | 粗粝、沙哑 |
| Rasalgethi | 知识讲解、信息型 |
| Laomedeia | 活泼 |
| Achernar | 柔和 |
| Alnilam | 坚定 |
| Schedar | 平稳、均衡 |
| Gacrux | 成熟 |
| Pulcherrima | 直接、有推进感 |
| Achird | 友好 |
| Zubenelgenubi | 日常、随意 |
| Vindemiatrix | 温柔 |
| Sadachbia | 生动 |
| Sadaltager | 专业、有知识感 |
| Sulafat | 温暖 |
