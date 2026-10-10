# 使用与配置 · Usage

Python 3.10+、Pillow、FFmpeg/ffprobe。完整渲染需要 Node.js 22+ 与 npm/npx；截图助手使用 Codex Playwright 包装脚本，也可由宿主浏览器提供截图。KIE 配音需要自己的服务账号。

Python 3.10+, Pillow and FFmpeg/ffprobe. Full rendering requires Node.js 22+ and npm/npx. Capture uses a Codex Playwright wrapper or host browser tools. KIE narration requires your own account.

## 检查入口 · Checks

从仓库根目录执行；替换命令中的示例文件路径。
Run from the repository root and replace example paths with your files.

```bash
python3 skills/ai-product-screenshot-video-v3/scripts/list_styles.py
python3 skills/ai-product-screenshot-video-v3/scripts/test_hybrid_builder.py
python3 skills/ai-product-screenshot-video-v3/scripts/test_stable_evidence.py
```

## 工作目录 · Working directory

每个任务使用独立输出目录，保存原始资料、运行配置和审核结果。
Keep source assets, configuration and review records in a separate directory for each task.

[中文示例](../examples/brief.zh.md) · [English brief](../examples/brief.en.md)

## 视频环境 · Video environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

- KIE_API_KEY：仅在调用 KIE 配音时需要，从环境读取。 / Required for KIE speech calls; read from the environment.
- PLAYWRIGHT_CLI：现有 Codex Playwright 包装脚本路径。 / Path to a Codex Playwright wrapper.
- FFMPEG_BIN：配音后处理的可选 FFmpeg 路径。 / Optional FFmpeg path for speech post-processing.
- HYPERFRAMES_VERSION：当前渲染助手默认 0.7.65，可覆盖；这是项目基线，不是对最新版的声明。 / Default 0.7.65 is a project baseline, not a claim about the latest release.

渲染助手通过 npm/npx 安装 HyperFrames 和项目依赖，首次渲染需要联网。检查宿主工具规则后再执行。
The helper downloads HyperFrames and project dependencies via npm/npx. Check your host's tool rules before running it.
