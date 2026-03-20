# Changelog

All notable changes to this project will be documented in this file.

## [0.0.5] - 2026-03-20

### Added
- 生图模型探测机制重构
  - 新增 `IMAGE_GEN_PROVIDER_MAP` 注册表，覆盖国内外 13 个生图 Provider
  - 支持的 Provider：ali-bailian/wanx、minimax-cn/image-01、baidu、tencent、zhipu、sensetime、bytedance、openai/dall-e-3、google/imagen-3、stability-ai、replicate、aws-bedrock、azure-openai
  - 初筛（input/api含image）→ 实测调用API → 缓存24小时
- 探测结果缓存机制（`~/.cache/wechat-mp-auto/image_models_cache.json`）

### Changed
- `get_ai_model_options()` 适配新探测逻辑，无可用模型时给出明确提示

## [0.0.4] - 2026-03-19

### Added
- 智能配图：AI 生图 + Pexels/Unsplash 图库
- 图片来源选择引导机制
- 本地+网络重复度检测
- 三阶段完整性检查
- 5种主题切换（default, henge, shuimo, wenyan, macaron）

## [0.0.3] - 2026-03-18

### Added
- 文章写作 Skill
- Markdown 转微信 HTML
- 敏感词检测

## [0.0.2] - 2026-03-17

### Added
- 微信公众号认证和 Token 管理
- 草稿发布 Skill

## [0.0.1] - 2026-03-16

### Added
- 项目初始化
- 基础架构搭建
