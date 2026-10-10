# AI 产品演示视频

把产品官网、界面截图和讲解文案制作成竖屏演示视频。画面围绕真实产品证据展开，标题、字幕和转场负责组织节奏，让信息清楚，也让观看过程更流畅。

**中文** · [English](README.en.md)

由叶轶伦在实际项目中持续迭代，整理当前可分享的工作流、辅助脚本与参考资料。保留已有来源和许可，具体说明见 [NOTICE](NOTICE.md)。

## 可以做什么

- 按文案匹配官网与界面截图，保留来源记录。
- 使用连续旁白，对齐句子与字幕，保持声音连贯。
- 提供六种视觉风格，支持混合场景布局。
- 保留分镜、截图、配音配置、预览和渲染结果。

## 工作流程

研究 → 截图审核 → 文案与分镜 → 配音 → 动态排版 → 检查与导出

## 开始使用

先安装下方依赖，再复制 Skills。已有同名版本时请先备份；套件中的目录保持同级。

```bash
git clone https://github.com/ElliottYip/product-demo-video-skill.git
cd product-demo-video-skill
mkdir -p ~/.codex/skills
cp -R skills/* ~/.codex/skills/
```

在新会话中调用：

```text
使用 $ai-product-screenshot-video-v3，根据我提供的产品网址和截图制作 30 秒竖屏介绍。先核对功能和画面来源，再提出文案、分镜与视觉风格。
```

## 运行要求

Python 3.10+、Pillow、FFmpeg/ffprobe。完整渲染需要 Node.js 22+ 与 npm/npx；截图助手使用 Codex Playwright 包装脚本，也可由宿主浏览器提供截图。KIE 配音需要自己的服务账号。

[详细配置与检查命令](docs/USAGE.md)

## 模块导航

- [ai-product-screenshot-video-v3](skills/ai-product-screenshot-video-v3/SKILL.md)

examples/ 提供可改写的任务简报；docs/ 记录配置、检查与版本来源。

## 当前版本

以当前安装的 V3 为入口。v1 使用截图卡片，v2 引入 HyperFrames；v3 增加混合布局、风格预设、连续配音对齐和截图稳定性检查。保留 V3 使用的辅助脚本，不重复打包旧版入口。

[迭代说明](CHANGELOG.md) · [验证记录](docs/VERIFICATION.md)

## 使用范围

默认面向中文 9:16 产品信息流。浏览器、配音与渲染依赖需要自行配置，包内不包含账号凭据。
