# wechat-mp-auto

微信公众号自动化 Skill - 从选题到发布的全流程自动化

[![Python Version](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![Version](https://img.shields.io/badge/version-v0.0.9-blue)](SKILL.md)

## 功能特性

本 Skill 由 **AI 模型作为编排者**，Python 代码提供原子化工具能力。AI 阅读 SKILL.md 后自行决定调用哪些工具，完成全部流程。

- **选题调研** - 级联搜索（Tavily → DuckDuckGo → 百度），多源自动切换
- **文章写作** - AI 根据提示词生成 Markdown，Python 负责格式转换
- **智能配图** - Pexels/Unsplash 图库搜索 + AI 生图（可选择）
- **图片处理** - 调整微信尺寸、压缩
- **内容审核** - 本地+网络重复度检测、敏感词扫描
- **模板管理** - 5 种本地主题切换（default/macaron/shuimo/wenyan/houge）
- **草稿发布** - 一键推送到公众号草稿箱

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置凭证

在 `~/.config/wechat-mp-auto/config.json` 中配置微信公众号凭证：

```json
{
  "app_id": "your_app_id",
  "app_secret": "your_app_secret"
}
```

或设置环境变量：

```bash
export WECHAT_APP_ID="your_app_id"
export WECHAT_APP_SECRET="your_app_secret"
```

### 3. 可选：配置图片生成 API

首次使用时系统会引导选择图片来源方式，支持以下两种：

**图片接口检索（推荐，无需信用卡）：**
```bash
export PEXELS_API_KEY="your_pexels_key"
export UNSPLASH_API_KEY="your_unsplash_key"
```
注册地址：Pexels https://www.pexels.com/api/ | Unsplash https://unsplash.com/developers



### 4. 可选：配置网络重复度检测

**Tavily：**
```bash
export TAVILY_API_KEY="your_tavily_key"
```

## 使用方法

本 Skill 由 **AI 模型作为编排者**，所有流程通过 AI 读取 SKILL.md 后自行调用工具完成，无需手动编写 Python 脚本。

**详细工具说明和编排流程见 [SKILL.md](./SKILL.md)。**

以下代码仅供手动调试参考：

```python
from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from skills.content_reviewer import ContentReviewerSkill

# 调研
research = TopicResearchSkill().research_topic("AI大模型应用")

# 生成大纲
outline = TopicResearchSkill().generate_outline("AI大模型应用", research)

# 内容审核（Markdown 生成后）
review = ContentReviewerSkill().review_article({"markdown": markdown_text})
if not review["passed"]:
    print("审核未通过:", review)

# 转换 HTML
html = ArticleWriterSkill().convert_to_html(markdown_text, theme="macaron")

# 上传图片
result = MaterialSkill().upload_image("/path/to/image.jpg")

# 创建草稿
DraftSkill().create_draft([{"title": "...", "content": html, ...}])
```

## 支持的主题

| 主题 | 说明 |
|------|------|
| macaron | 马卡龙风格（粉紫色 #FF6B9D） |
| shuimo | 水墨风格（深灰蓝 #2C3E50） |
| wenyan | 文雁风格（深蓝绿 #0066FF） |
| houge | 猴哥风格（深蓝橙 #6b5b8a） |
| default | 默认风格（蓝色 #007AFF） |

## 内容审核详解

### 本地重复度检测
- **算法**：n-gram + Jaccard 相似度
- **阈值**：30% 以上判定为重复
- **存储**：自动保存到 `~/.cache/wechat-mp-auto/article_history.json`

### 网络重复度检测
- **算法**：提取关键句 → Tavily 搜索 → 相似度比对
- **阈值**：10% 以上判定为匹配
- **特点**：异步执行，不阻塞主流程
- **缓存**：搜索结果缓存到 `~/.cache/wechat-mp-auto/search_cache.json`

### 敏感词检测
检测词汇：`反动、暴力、色情、赌博、毒品、诈骗、谣言`

## 项目结构

```
wechat-mp-auto/
├── SKILL.md                    # AI 编排指南（本 Skill 的核心文档）
├── metadata.json                # Skill 元数据
├── README.md                   # 本文件（人类参考）
├── requirements.txt           # Python 依赖
├── pyproject.toml             # 项目配置
├── src/
│   ├── config.py             # 配置管理
│   ├── token_manager.py      # 微信 Access Token 管理
│   ├── exceptions.py         # 异常定义
│   └── skills/
│       ├── topic_research.py  # 调研工具（research_topic / generate_outline）
│       ├── article_writer.py  # 格式转换工具（convert_to_html）
│       ├── image_generator.py # 图片工具（search_image / generate_image）
│       ├── material_skill.py # 图片上传工具（upload_image）
│       ├── draft_skill.py     # 草稿推送工具（create_draft）
│       └── ...                # 其他辅助模块
└── themes/                   # HTML 主题配色
    ├── default.yaml
    ├── macaron.yaml
    ├── shuimo.yaml
    ├── wenyan.yaml
    └── houge.yaml
```

## 注意事项

1. **图片尺寸**：封面 900x500px，插图建议 640-1080px 宽度
2. **图片格式**：支持 jpg/jpeg/png/gif/webp
3. **API 限制**：微信素材上传有频率限制，大批量操作注意节奏
4. **Token 缓存**：access_token 会自动缓存，无需手动处理
5. **网络检测**：需要配置 TAVILY_API_KEY 才能启用网络重复度检测
6. **数据分析权限**：文章统计数据（阅读量/点赞/转发）API 仅**服务号**或**已认证的订阅号**可用。普通订阅号调用会返回 404，如需此功能请升级公众号类型。

## 常见问题

**Q: 提示 "access_token 无效" 怎么办？**
> 删除 `~/.cache/wechat-mp-auto/token.json` 文件，重新运行

**Q: 图片上传失败？**
> 检查图片格式和大小，微信限制 20MB

**Q: 如何获取 app_id 和 app_secret？**
> 登录微信公众号后台 → 设置与开发 → 基本配置

**Q: 网络重复度检测需要配置什么？**
> 需要配置 TAVILY_API_KEY，可在 https://tavily.com/ 注册获取

**Q: 文章没有插图怎么办？**
> 检查 ~/.cache/wechat-mp-auto/images/ 目录是否有图片，或配置 PEXELS_API_KEY 自动生成

## 许可证

MIT License - see [LICENSE.txt](LICENSE.txt)

## 贡献

欢迎提交 Issue 和 Pull Request！
