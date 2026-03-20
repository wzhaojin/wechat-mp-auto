# wechat-mp-auto - 微信公众号自动化 Skill

**版本**: v0.0.4  
**描述**: 微信公众号文章从选题到发布的全流程自动化

---

## 功能特性

- 选题调研 - 级联搜索（ Tavily → DuckDuckGo → 百度），多源自动切换
- 文章写作 - Markdown 转微信 HTML（**自动插入封面和章节插图**）
- 智能配图 - AI 生图 + Pexels/Unsplash 图库（首次引导选择图片来源）
- **内容审核** - 本地+网络重复度检测、敏感词扫描、**三阶段完整性检查**
- 本地主题 - 5种主题切换（**支持预览**）
- 数据分析 - 阅读量、点赞数统计

---

## 安装

```bash
pip install -r requirements.txt
```

### 配置

1. 在 `~/.config/wechat-mp-auto/config.json` 配置微信凭证
2. 或在 `~/.openclaw/.env` 中配置环境变量
3. 可选：配置图片API密钥（PEXELS_API_KEY、UNSPLASH_API_KEY等）

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

**图片来源有两种方式，首次使用时系统会引导选择：**

#### 方式一：图片接口检索（推荐）

**Pexels**（推荐）
- 官网：https://www.pexels.com/api/
- 免费额度：每月 200 请求
- 获取 Key：注册 → API → Your API Key

**Unsplash**
- 官网：https://unsplash.com/developers
- 免费额度：每月 50 请求
- 获取 Key：Create New Application → Access Key

```bash
# 写入 ~/.openclaw/.env
PEXELS_API_KEY=你的Key
UNSPLASH_API_KEY=你的Key
```

#### 方式二：AI 生图

**支持的生图模型 Provider：**

| 分类 | Provider | 模型 | 说明 |
|------|----------|------|------|
| 国内 | ali-bailian | wanx2.1 | 阿里云通义万图 |
| 国内 | minimax-cn | image-01 | MiniMax 生图 |
| 国内 | baidu | ernie-vilg-v2 | 百度文心一格 |
| 国内 | tencent | hunyuan-image | 腾讯混元 |
| 国内 | zhipu | cogview-4 | 智谱 CogView |
| 国内 | sensetime | nova-smooth | 商汤 |
| 国内 | bytedance | sdxl-txt2img | 字节豆包 |
| 国外 | openai | dall-e-3 | OpenAI DALL-E 3 |
| 国外 | google | imagen-3 | Google Imagen 3 |
| 国外 | stability-ai | stable-diffusion-xl（SDXL） | Stability AI |
| 国外 | replicate | flux-schnell | Replicate Flux |
| 国外 | aws-bedrock | stability.stable-diffusion-xl-v1 | AWS Bedrock |
| 国外 | azure-openai | dall-e-3 | Azure DALL-E 3 |

**配置方式：**
在 OpenClaw 配置文件 `~/.openclaw/openclaw.json` 中配置相应的模型和 API Key。

**探测机制：**
- **初筛**：读取 OpenClaw 配置时，自动过滤 `input` 包含 `image` 或 `api` 类型包含 `image` 的模型
- **实测探测**：对初筛通过的模型，实际调用其图像生成 API，验证是否真正具备生图能力
- **缓存**：探测结果缓存 24 小时，避免重复探测

---

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
- **算法**：提取关键句 → 级联搜索 → 相似度比对
- **阈值**：10% 以上判定为匹配
- **特点**：异步执行，不阻塞主流程

### 级联搜索机制

选题调研和网络检测均采用**级联搜索**策略，多个搜索源按优先级自动切换：

| 优先级 | 搜索源 | 说明 | 需要 API Key |
|--------|--------|------|-------------|
| 1 | Tavily | 推荐，快速准确 | 是（免费额度1000/月） |
| 2 | DuckDuckGo | 无需 Key，需可访问外网 | 否 |
| 3 | 百度 | 国内可用，无需 Key | 否 |

**搜索流程：**
```
尝试 Tavily → [失败] → DuckDuckGo → [失败] → 百度 → [全部失败] → 返回默认结果
```

**特点：**
- 任何一个源成功即返回，不继续尝试后续
- 失败原因详细记录到日志
- 网络检测中的限流（429）会自动重试一次

### 敏感词检测
检测词汇：
```
反动、暴力、色情、赌博、毒品、诈骗、谣言
```

---

## 图片来源选择

首次调用 `write_article(generate_images=True)` 或图片生成方法时，系统会引导选择图片来源方式。

### 选择流程

1. **图片来源选择**
   - `AI生图`：调用 AI 模型生成图片（需选择模型）
   - `图片接口检索`：从 Pexels/Unsplash 图库搜索（需配置 API key）

2. **模型选择**（选择 AI 生图时）
   系统从 OpenClaw 配置中动态读取生图模型列表，并通过实测探测验证模型是否真正具备生图能力。
   如果未配置任何生图模型，系统会提示配置或改用图片检索方式。

### 偏好持久化

选择结果写入 `~/.config/wechat-mp-auto/config.json`，后续调用不再提示。
如需更改，删除配置文件中 `image_source` 和 `ai_model` 字段后重新触发。

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `PEXELS_API_KEY` | Pexels 免费图库 API Key |
| `UNSPLASH_API_KEY` | Unsplash 免费图库 API Key |

---

## 模板预览

查看所有 5 个模板的视觉效果：

```python
from skills.article_writer import ArticleWriterSkill
writer = ArticleWriterSkill()
html = writer.preview_theme()
# 用 canvas 渲染：
# canvas.present(url="data:text/html;charset=utf-8," + html)
```

返回包含全部 5 个模板（default、shuimo、wenyan、macaron、houge）的合并预览图，不同模板用不同底色区分，可直观对比各主题配色效果。

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
│       ├── image_generator.py # 配图生成（Pexels/Unsplash）
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

- `default` - 默认主题（蓝色 #007AFF）
- `macaron` - 马卡龙风格（粉紫色 #FF6B9D）
- `shuimo` - 水墨风格（深灰蓝 #2C3E50）
- `wenyan` - 文雁风格（深蓝绿 #0066FF）
- `houge` - 猴哥风格（深蓝橙 #1A1A2E）

---

## 安全规范

- Skill 代码中不存储任何凭证
- 日志中不出现完整密钥
- 发布前可使用 `--check-only` 参数进行完整性检查，仅检查不推送

---

## 注意事项

1. 微信"文章模板"无开放 API，无法下载/上传
2. 图片优先使用 Pexels，无效则切换 Unsplash
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
