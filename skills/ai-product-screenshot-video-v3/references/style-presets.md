# V3 style presets

Select with `--style <id>` or write `style_preset` in `storyboard.json`. If the user does not choose, infer one and report it before preview.

| ID | 中文名称 | Best fit |
|---|---|---|
| `kinetic-dark` | 深色动效科技 | AI 工具榜单、开发者产品、快节奏信息流 |
| `clean-editorial` | 明亮编辑杂志 | 效率工具、小红书、可信教程 |
| `brand-adaptive` | 品牌自适应 | 有明确品牌色、产品发布、单品推荐 |
| `premium-tech` | 克制高级科技 | B2B、企业服务、专业测评 |
| `viral-neon` | 高冲击爆款霓虹 | 抖音/TikTok 强 Hook、年轻受众 |
| `evidence-first` | 极简证据优先 | 功能验证、价格对比、需要更大截图 |

All presets share the same evidence rules: screenshots stay axis-aligned and pixel-stable; only editorial text, feature cards, particles, and captions animate. `brand-adaptive` may override `primary`, `secondary`, `signal`, `bg_a`, and `bg_b` under `theme`, after extracting colors from an official logo or screenshot. Never sacrifice subtitle contrast or evidence readability to match a brand color.
