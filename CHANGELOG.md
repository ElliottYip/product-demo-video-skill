# 迭代与打包说明 · Packaging notes

## 2026-10-10 · Public snapshot

以当前安装的 V3 为入口。v1 使用截图卡片，v2 引入 HyperFrames；v3 增加混合布局、风格预设、连续配音对齐和截图稳定性检查。保留 V3 使用的辅助脚本，不重复打包旧版入口。

The current V3 entry builds on V1 screenshot cards and V2 HyperFrames compositions, adding hybrid layouts, style presets, continuous-narration alignment and evidence-stability checks. Supporting scripts remain included; older entry points are not duplicated.

- 保留当前工作流、测试和配套规范，增加中英文说明。
- 不包含历史备份、缓存、运行凭据和生成产物。
- 此版本是当前安装内容的公开快照，不重建此前的 Git 历史。
- This package is a snapshot of current installed content; it does not reconstruct earlier Git history.
