# wechat-mp-auto

微信公众号自动化 Skill - 从选题到发布的全流程自动化

[![Python Version](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![Version](https://img.shields.io/badge/version-v0.0.4-blue)](SKILL.md)

## 功能特性

- **选题调研** - 联网搜索可信源，自动生成文章大纲
- **文章写作** - Markdown 转微信 HTML，支持多种格式，**自动插入封面和章节插图**
- **智能配图** - Pexels/Unsplash 无版权图片 + OpenAI DALL-E AI 生成
- **图片处理** - 自动去水印、调整微信尺寸、压缩
- **内容审核** - 本地+网络重复度检测、敏感词扫描、**三阶段完整性检查**
- **模板管理** - 本地 ↔ 微信公众平台双向同步
- **草稿发布** - 一键推送到公众号草稿箱
- **数据分析** - 阅读量、点赞数统计

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

**Pexels（推荐，无需信用卡）：**
```bash
export PEXELS_API_KEY="your_pexels_key"
```

**Unsplash：**
```bash
export UNSPLASH_API_KEY="your_unsplash_key"
```

**OpenAI DALL-E（AI 生成）：**
```bash
export OPENAI_API_KEY="sk-..."
```

### 4. 可选：配置网络重复度检测

**Tavily：**
```bash
export TAVILY_API_KEY="your_tavily_key"
```

## 使用方法

### 命令行发布文章

```bash
cd src
python3 publish.py --markdown ../article.md --title "文章标题" --author "作者"
```

**完整参数：**
```bash
python3 publish.py \
  --markdown article.md \
  --title "我的文章" \
  --author "贾维斯" \
  --cover cover.jpg \
  --theme macaron \
  --check-only
```

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| --markdown | -m | Markdown 文件路径 | 必填 |
| --title | -t | 文章标题 | 文件名 |
| --author | -a | 作者 | 贾维斯 |
| --cover | -c | 封面图路径 | 自动查找 |
| --source-url | -s | 原文链接 | https://openclaw.ai |
| --theme | | 主题名称 | macaron |
| --check-only | | 仅检查不推送 | false |
| --verbose | -v | 显示详细日志 | false |

### Python API

#### 1. 自动化文章生成（带配图）

```python
from skills.article_writer import ArticleWriterSkill

writer = ArticleWriterSkill()

# 定义文章大纲
outline = {
    'title': 'AI 助手介绍',
    'sections': [
        {'name': '什么是 AI 助手', 'key_points': ['定义', '发展历史']},
        {'name': '功能特点', 'key_points': ['智能对话', '任务自动化']},
    ]
}

# 生成文章（generate_images=True 自动生成配图）
result = writer.write_article('主题', outline, generate_images=True)

# 返回结果包含：
# - result['markdown']: Markdown 内容（含图片语法）
# - result['html']: 转换后的 HTML
# - result['title']: 文章标题
# - result['cover_path']: 封面图路径

print(result['markdown'])
```

#### 2. 三阶段完整性检查

```python
from publish import check_article_integrity

# 检查点1：Markdown 生成后
result1 = check_article_integrity(markdown=markdown, stage="markdown")

# 检查点2：HTML 转换后
result2 = check_article_integrity(markdown=markdown, html=html, stage="html")

# 检查点3：草稿上传后
result3 = check_article_integrity(draft_content=draft_content, stage="draft")

# 检查结果
if not result1['passed']:
    print(f"问题: {result1['issues']}")
if result1['warnings']:
    print(f"警告: {result1['warnings']}")
```

#### 3. 内容审核

```python
from skills.content_reviewer import ContentReviewerSkill

reviewer = ContentReviewerSkill()

# 审核文章
article = {'markdown': markdown, 'content': html}
result = reviewer.review_article(article)

# 结果包含：
print(f'通过: {result["passed"]}')
print(f'重复度: {result["plagiarism"]["similarity"]}%')
print(f'是否重复: {result["plagiarism"]["is_duplicated"]}')
print(f'敏感词: {result["prohibited"]["violations"]}')

# 手动检查网络重复度（异步）
network_result = reviewer.check_network_plagiarism(markdown)
# 等待后获取结果
import time
time.sleep(15)
final = reviewer.get_network_result(network_result)
print(f'网络重复度: {final["match_ratio"]}%')
```

#### 4. 完整发布流程

```python
from skills.article_writer import ArticleWriterSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from publish import check_article_integrity
from config import Config
from token_manager import TokenManager

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
token_mgr = TokenManager(app_id, app_secret)

writer = ArticleWriterSkill()
material = MaterialSkill(token_mgr)
draft = DraftSkill(token_mgr)

# 1. 生成文章
outline = {
    'title': '我的文章',
    'sections': [{'name': '第一章', 'key_points': ['要点1']}]
}
result = writer.write_article('主题', outline, generate_images=True)
markdown = result['markdown']
html = result['html']

# 2. 检查点1
check_article_integrity(markdown=markdown, stage="markdown")

# 3. 检查点2
check_article_integrity(markdown=markdown, html=html, stage="html")

# 4. 上传图片到微信
html_with_urls, processed = insert_images_to_content(html, material)

# 5. 创建草稿
article = {
    'title': result['title'],
    'author': '贾维斯',
    'content': '<meta charset="utf-8">\n' + html_with_urls,
    'thumb_media_id': cover_media_id,
    'content_source_url': 'https://openclaw.ai'
}
draft_result = draft.create_draft([article])

# 6. 检查点3
draft_content = draft.get_draft(draft_result['media_id'])['content']
check_article_integrity(draft_content=draft_content, stage="draft")
```

## 支持的主题

| 主题 | 说明 |
|------|------|
| macaron | 马卡龙风格（粉紫色） |
| shuimo | 水墨风格 |
| wenyan | 文言风格 |
| henge | 猴哥风格 |
| default | 默认风格 |

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
├── README.md              # 本文件
├── SKILL.md              # OpenClaw Skill 定义
├── LICENSE.txt           # MIT 许可证
├── requirements.txt      # Python 依赖
├── pyproject.toml       # 项目配置
├── test_all.py          # 测试脚本
├── test_conversion.py   # 转换测试
├── src/
│   ├── config.py           # 配置管理
│   ├── token_manager.py   # Token 缓存
│   ├── exceptions.py      # 异常定义
│   ├── publish.py         # 发布脚本（含检查函数）
│   └── skills/
│       ├── article_writer.py      # Markdown 转 HTML + 自动插图
│       ├── image_generator.py    # 图片生成
│       ├── image_processor.py    # 图片处理
│       ├── content_reviewer.py   # 内容审核（重复度、敏感词、网络检测）
│       ├── material_skill.py     # 素材管理
│       ├── draft_skill.py        # 草稿箱
│       ├── publish_skill.py      # 发布管理
│       ├── topic_research.py     # 选题调研
│       ├── template_skill.py    # 模板管理
│       └── analytics_skill.py   # 数据分析
├── utils/                     # 工具函数
├── formatters/               # 格式化
└── themes/                   # 主题配置
    ├── macaron.yaml
    ├── shuimo.yaml
    └── ...
```

## 注意事项

1. **图片尺寸**：封面 900x500px，插图建议 640-1080px 宽度
2. **图片格式**：支持 jpg/jpeg/png/gif/webp
3. **API 限制**：微信素材上传有频率限制，大批量操作注意节奏
4. **Token 缓存**：access_token 会自动缓存，无需手动处理
5. **网络检测**：需要配置 TAVILY_API_KEY 才能启用网络重复度检测

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
