# wechat-mp-auto - 微信公众号自动化 Skill

**版本**: 1.2  
**描述**: 微信公众号文章从选题到发布的全流程自动化

---

## 功能特性

- 选题调研 - 联网搜索可信源
- 文章写作 - Markdown 转微信 HTML（**自动插入封面和章节插图**）
- 智能配图 - Pexels/Unsplash 无版权图片
- **内容审核** - 本地+网络重复度检测、敏感词扫描、**三阶段完整性检查**
- 本地主题 - 5种主题切换
- 数据分析 - 阅读量、点赞数统计

---

## 快速开始

### 1. 配置微信公众号凭证

获取路径：
1. 登录 https://mp.weixin.qq.com/
2. 进入 **开发** → **基本配置**
3. 获取 **AppID** 和 **AppSecret**
4. 设置 **IP 白名单**

配置文件：`~/.config/wechat-mp-auto/config.json`

```json
{
  "app_id": "wx开头的18位ID",
  "app_secret": "32位密钥",
  "default_template": {
    "type": "local",
    "id": "shuimo"
  }
}
```

### 2. 配置图片 API（可选）

**Pexels**（推荐）
- 官网：https://www.pexels.com/api/
- 免费额度：每月 200 请求
- 获取 Key：注册 → API → Your API Key

**Unsplash**
- 官网：https://unsplash.com/developers
- 免费额度：每月 50 请求
- 获取 Key：Create New Application → Access Key

**OpenAI DALL-E**（AI 生成图片）
- 官网：https://platform.openai.com/
- 获取 Key：API Keys

配置方式：
```bash
# 写入 ~/.openclaw/.env
PEXELS_API_KEY=你的Key
UNSPLASH_API_KEY=你的Key
OPENAI_API_KEY=你的Key
```

### 3. 配置网络重复度检测（可选）

**Tavily**（推荐）
- 官网：https://tavily.com/
- 免费额度：每月 1000 请求
- 获取 Key：注册 → API Key

```bash
# 方式1：环境变量
export TAVILY_API_KEY=你的Key

# 方式2：配置文件
# ~/.config/wechat-mp-auto/config.json
{
  "tavily_api_key": "你的Key"
}
```

---

## 内容审核

### 本地重复度检测
- **算法**：n-gram + Jaccard 相似度
- **阈值**：30% 以上判定为重复
- **历史记录**：自动保存到 `~/.cache/wechat-mp-auto/article_history.json`

### 网络重复度检测
- **算法**：提取关键句 → Tavily 搜索 → 相似度比对
- **阈值**：10% 以上判定为匹配
- **特点**：异步执行，不阻塞主流程

### 敏感词检测
检测词汇：
```
反动、暴力、色情、赌博、毒品、诈骗、谣言
```

---

## 三阶段完整性检查

| 检查点 | 时机 | 检查内容 |
|--------|------|----------|
| 检查点1 | Markdown 生成后 | 标题数量、图片语法、文件是否存在 |
| 检查点2 | HTML 转换后 | HTML 标签完整性、图片 src 是否为空、是否有本地图片未上传 |
| 检查点3 | 草稿上传后 | 草稿中的图片（src/data-src）、编码检测 |

---

## 目录结构

```
wechat-mp-auto/
├── SKILL.md                    # 本文档
├── _meta.json                   # 元数据
├── metadata.json                # Skill 描述
├── LICENSE.txt                  # 许可证
├── README.md                    # 人类使用说明
├── package.json                 # 依赖定义
├── pyproject.toml              # 项目配置
├── requirements.txt            # Python 依赖
├── test_all.py                # 测试脚本
├── test_conversion.py         # 转换测试
├── src/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── token_manager.py       # Token 管理
│   ├── exceptions.py         # 异常定义
│   ├── first_time_setup.py   # 首次使用引导
│   ├── publish.py            # 发布脚本（含检查函数）
│   └── skills/
│       ├── __init__.py
│       ├── base_skill.py      # 基础类
│       ├── topic_research.py # 选题调研
│       ├── article_writer.py # 文章写作（含 Markdown 转 HTML、自动插图）
│       ├── image_generator.py # 配图生成（Pexels/Unsplash/DALL-E）
│       ├── image_processor.py # 图片处理
│       ├── content_reviewer.py # 内容审核（重复度、敏感词、网络检测）
│       ├── template_design.py # 模板设计
│       ├── template_skill.py # 本地模板管理
│       ├── template_sync.py  # 模板同步（注：无 API）
│       ├── draft_skill.py   # 草稿箱管理
│       ├── publish_skill.py # 发布管理
│       ├── material_skill.py # 素材管理
│       └── analytics_skill.py # 数据分析
├── utils/
│   ├── __init__.py
│   ├── logger.py             # 日志（脱敏）
│   └── validators.py         # 参数验证
├── formatters/
│   └── __init__.py
└── themes/                    # 本地主题
    ├── default.yaml
    ├── macaron.yaml
    ├── shuimo.yaml
    ├── wenyan.yaml
    └── houge.yaml
```

---

## 本地主题

- `default` - 默认主题
- `macaron` - 马卡龙风格（粉紫色）
- `shuimo` - 水墨中国风
- `wenyan` - 现代科技风
- `henge` - 猴哥风格

---

## 安全规范

- Skill 代码中不存储任何凭证
- 日志中不出现完整密钥
- 发布前必须用户确认

---

## 注意事项

1. 微信"文章模板"无开放 API，无法下载/上传
2. 图片优先使用 Pexels，无效则切换 Unsplash，最后尝试 DALL-E
3. Markdown 转 HTML 内置在 article_writer 中
4. 网络重复度检测需要配置 TAVILY_API_KEY
5. 文章生成时会自动查找 cache 目录中的已有图片

---

## 使用示例

### 1. 生成文章（带自动配图）
```python
from skills.article_writer import ArticleWriterSkill

writer = ArticleWriterSkill()

outline = {
    'title': 'AI 助手介绍',
    'sections': [
        {'name': '什么是 AI 助手', 'key_points': ['定义', '发展历史']},
        {'name': '功能特点', 'key_points': ['智能对话', '任务自动化']},
    ]
}

result = writer.write_article('主题', outline, generate_images=True)
# result 包含: markdown, html, title, cover_path 等
```

### 2. 发布文章（含三阶段检查）
```python
from publish import check_article_integrity

# 检查点1
check_article_integrity(markdown=md, stage="markdown")

# 检查点2
check_article_integrity(markdown=md, html=html, stage="html")

# ... 上传图片、创建草稿 ...

# 检查点3
check_article_integrity(draft_content=content, stage="draft")
```

### 3. 内容审核
```python
from skills.content_reviewer import ContentReviewerSkill

reviewer = ContentReviewerSkill()

# 审核文章
result = reviewer.review_article({
    'markdown': markdown,
    'content': html
})

print(f'通过: {result["passed"]}')
print(f'重复度: {result["plagiarism"]["similarity"]}%')
print(f'敏感词: {result["prohibited"]["violations"]}')
```

---

## License

MIT
