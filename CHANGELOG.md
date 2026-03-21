# Changelog

All notable changes to this project will be documented in this file.

## [0.0.7] - 2026-03-21

### Changed
- 重构 `convert_to_html`：Theme YAML 完整读取，所有颜色/字体/间距从 YAML 配置读取，不再硬编码
- 5 个主题 YAML（default/houge/macaron/shuimo/wenyan）统一完整字段结构：colors/body/h1-h3/p/link/blockquote/ul/ol
- 列表改为语义化 `<ul>/<ol>/<li>` 结构

### Fixed
- `publish.py`：修复审核时 `html` 变量未定义的 bug
- `publish.py`：修复封面图占位符 `cover_image_url` 只替换第一处的问题，改为全局替换
- `publish.py`：新增章节图占位符 `*_url` 替换逻辑
- `publish.py`：新增草稿完整性检查中图片 URL 可访问性验证（HEAD 请求）
- `publish.py`：修复 `find_cover_image` 选中缩略图（_thumb）的问题
- `publish.py`：修复外部图片 URL 正则无法匹配 `data-src` 和 `https` 协议的问题

## [0.0.6] - 2026-03-21

### Added
- SKILL.md 新增「接口权限说明」表格，明确标注数据分析 API 仅服务号或已认证订阅号可用
- README.md 注意事项补充数据分析权限说明

### Fixed
- 统一 pyproject.toml 版本号（0.0.3 → 0.0.6），与 metadata.json 保持一致
- 删除临时文件 article_final.html、article_output.html

## [0.0.5] - 2026-03-20

### Added
- 生图模型探测机制重构
  - 新增 `IMAGE_GEN_PROVIDER_MAP` 注册表，覆盖国内外 13 个生图 Provider
  - 支持的 Provider：ali-bailian/wanx、minimax-cn/image-01、baidu、tencent、zhipu、sensetime、bytedance、openai/dall-e-3、google/imagen-3、stability-ai、replicate、aws-bedrock、azure-openai
  - 初筛（input/api含image）→ 实测调用API → 缓存24小时
- 探测结果缓存机制（`~/.cache/wechat-mp-auto/image_models_cache.json`）
- 级联搜索机制（TopicResearchSkill）
  - 支持 Tavily → DuckDuckGo → 百度 多源自动切换
  - 任何一个源成功即返回，失败自动尝试下一个
  - 失败原因详细记录，限流(429)自动重试

### Changed
- `get_ai_model_options()` 适配新探测逻辑，无可用模型时给出明确提示
- `TopicResearchSkill.research_topic()` 和内容审核网络检测均支持级联搜索

## [0.0.4] - 2026-03-19

### Added
- 智能配图：AI 生图 + Pexels/Unsplash 图库
- 图片来源选择引导机制
- 本地+网络重复度检测
- 三阶段完整性检查
- 5种主题切换（default, houge, shuimo, wenyan, macaron）

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
