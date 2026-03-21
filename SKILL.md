# wechat-mp-auto - 微信公众号自动化 Skill

**版本**: v0.0.9
**描述**: 微信公众号文章从选题到发布的全流程自动化

---

## 架构理念

本 Skill 由 **AI 模型作为编排者**，Python 代码提供原子化工具能力。AI 读取本 SKILL.md 后自行决定调用哪些工具、完成全部流程。

Python 代码不包含任何 AI 调用逻辑，所有生成、推理、判断均由 AI 模型完成。

---

## 工具清单

AI 可调用的所有工具如下，调用时请传入完整参数：

### 1. 调研工具

**`research_topic(topic: str, keywords: Optional[List[str]] = None) -> dict`**
- 输入：文章主题（字符串），可选的关键词列表（用于精细化搜索）
- 输出：`{"search_results": [...], "summary": "..."}`
- 作用：对给定主题进行网络调研，返回搜索结果摘要
- 内部级联：Tavily → DuckDuckGo → 百度，任一成功即返回

---

**`generate_outline(topic: str, research: dict) -> dict`**
- 输入：主题字符串 + research_topic 的返回结果
- 输出：
```json
{
  "title": "深度解析：XXX",
  "sections": [
    {"name": "引言", "description": "...", "key_points": ["要点1", "要点2"]},
    {"name": "核心内容", "description": "...", "key_points": [...]},
    ...
  ]
}
```
- 作用：根据调研结果生成文章大纲，包含 4 个标准章节（引言/核心内容/实践方法/结论）

---

### 2. 写作工具

**`convert_to_html(markdown: str, theme: str) -> str`**
- 输入：Markdown 格式文章内容 + 主题名称
- 输出：微信可用的 HTML 字符串
- 主题可选值：
  - `default` — 默认蓝色
  - `macaron` — 马卡龙粉紫色
  - `shuimo` — 水墨深灰蓝
  - `wenyan` — 文雁深蓝绿
  - `houge` — 猴哥深蓝橙

---

### 3. 图片工具

**`search_image(query: str, count: int) -> list`**
- 输入：搜索关键词（字符串），请求图片数量（整数）
- 输出：图片信息列表，每个元素含 `url`（下载链接）和 `local_path`（本地缓存路径）
- 作用：通过 Pexels/Unsplash 图库搜索并下载图片，返回本地文件路径
- 注意：如未配置图库 API Key，此工具不可用

---

**`generate_image(prompt: str, size: str) -> dict`**
- 输入：图片描述提示词（字符串），图片尺寸（字符串，格式如 `"1024x1024"`）
- 输出：`{"local_path": "本地文件路径"}`
- 作用：调用 AI 生图模型生成图片，返回本地保存路径

---

**`upload_image(file_path: str) -> dict`**
- 输入：本地图片文件路径（字符串）
- 输出：`{"media_id": "...", "url": "微信图片URL"}`
- 作用：将本地图片上传至微信素材库，返回微信图片 URL 和 media_id
- 注意：上传前需确保图片文件存在，支持 JPG/PNG

---

### 4. 内容审核工具

**`review_article(article: dict) -> dict`**
- 输入：文章对象，格式如下：
```json
{
  "markdown": "Markdown 内容（字符串）",
  "content": "HTML 内容（字符串，可选）"
}
```
- 输出：
```json
{
  "passed": true/false,
  "plagiarism": {"similarity": 0, "is_duplicated": false},
  "prohibited": {"violations": []}
}
```
- 作用：审核文章内容，返回是否通过及问题列表

---

### 5. 草稿工具

**`create_draft(articles: list, auto_upload_thumb: bool = False) -> dict`**
- 输入：文章列表，每篇格式如下：
```json
{
  "title": "文章标题",
  "author": "贾维斯",
  "content": "HTML内容（字符串）",
  "thumb_media_id": "封面缩略图的media_id",
  "content_source_url": "原文链接，可填 https://openclaw.ai"
}
```
- 输出：`{"media_id": "草稿ID", "msg": "..."}`
- 作用：将文章推送到微信公众号草稿箱

---

## AI 编排流程

AI 读取本 SKILL.md 后，按以下步骤执行。每一步都需要显式调用对应工具：

```
第一步：调研
  → 调用 research_topic(topic)
  → 获得 search_results 和 summary

第二步：生成大纲
  → 调用 generate_outline(topic, research结果)
  → 获得 title 和 sections（含章节名、描述、要点）

第三步：组装提示词并生成文章
  → 根据第二步的大纲，自行组装提示词（见下方"提示词组装规范"）
  → 用大模型根据提示词生成完整的 Markdown 文章
  → 注意：大模型直接输出 Markdown，不需要调用任何工具来"写作"

第四步：内容审核
  → 调用 review_article({"markdown": 第三步生成的Markdown})
  → 如 passed=false 或存在 prohibited.violations，应重新生成或修改内容
  → 审核通过后再进入第五步

第五步：转换格式
  → 调用 convert_to_html(第三步生成的Markdown, theme参数)
  → 获得 HTML 字符串

第六步：生成并上传配图
  → 生成封面图：
    - 优先调用 search_image(文章标题关键词, count=5)，下载到本地
    - 或调用 generate_image(封面图描述, size="900x500")，得到本地路径
  → 调用 upload_image(封面图本地路径) → 获得 thumb_media_id 和封面微信URL
  → 为每个章节生成一张配图：
    - 优先调用 search_image(章节标题关键词, count=3)
    - 或调用 generate_image(章节图描述, size="900x500")
  → 分别调用 upload_image(章节图本地路径) → 获得章节图的微信URL

第七步：注入图片URL
  → 将第六步获得的微信图片URL，一一替换到 HTML 中对应占位符：
    - 封面图：`src="cover_image_url"` → 替换为封面微信URL
    - 章节图：`src="章节标题_url"` → 替换为对应章节的微信URL
  → **每个占位符必须单独对应**，封面和每个章节图的 src 均不同
  → 如 HTML 中尚无图片标签，则在对应位置插入：
    - 封面图：文章开头，标题后插入 <img src="封面微信URL">
    - 章节图：每个 ## 章节标题后插入 <img src="对应章节微信URL">

第八步：推送草稿
  → 调用 create_draft([{
    "title": 文章标题,
    "author": "贾维斯",
    "content": 注入了图片URL的完整HTML,
    "thumb_media_id": 封面图的media_id,
    "content_source_url": "https://openclaw.ai"
  }])
  → 获得草稿ID，流程完成
```

---

---

## 批量生成多篇文章

单篇文章流程（第一步至第八步）为一轮。当需要生成多篇文章时，按以下方式循环执行：

```
对第 1 篇文章执行第一步至第八步
  → 等待第八步完成后，再开始第 2 篇

对第 2 篇文章执行第一步至第八步
  → 等待完成后，再开始第 3 篇

... 以此类推
```

每篇文章之间相互独立，主题、大纲、写作风格均可不同。

---

## 提示词组装规范

第三步中，AI 组装提示词时应包含以下部分，以结构化方式呈现：

```
## 文章主题
{topic}

## 文章大纲
{section_name_1}
  描述：{section.description}
  关键要点：{section.key_points列表}

{section_name_2}
  ...

## 调研资料摘要
{research.summary}
（包含3-5条最相关的搜索结果摘要）

## 写作风格要求
{从以下选项中选择或组合：}
- 口语化 / 正式 / 俏皮 / 专业 / 通俗易懂
- 段落之间逻辑连贯，有真知灼见
- 禁止空洞套话

## 输出格式要求
- 主标题：# 标题（一级，仅一个）
- 章节标题：## 二级标题
- 子章节：### 三级标题
- 重点词语：**加粗**
- 代码块：```bash 代码 ``` 格式
- 列表：- 格式
- 全文字数：不超过 7200 字
- 禁止重复章节或段落

## 配图标记说明
- 封面图位置：在文章开头，标题后插入 ![封面](cover_image_url)
- 章节图位置：在每个 ## 章节标题正后方插入 ![章节标题](章节标题_url)
- **重要**：每个章节的占位符必须是**唯一的**，占位符名称 = 章节标题（不含空格和特殊字符）+"_url"
  - 示例：章节"OpenClaw 简介" → `![OpenClaw简介](OpenClaw简介_url)`
  - 示例：章节"环境准备" → `![环境准备](环境准备_url)`
  - **禁止**所有章节图使用相同的占位符（如 `section_image_url`）
- 占位符说明：图片 URL 暂时填入上述占位符，后续第五、六步会上传真实微信图片URL并替换

## 重要约束
- 输出内容到此为止，不输出任何检查清单、打分表、自评或额外说明
- 全文每个章节只出现一次，不得重复输出任何章节或段落
```

---

## 配置要求

### 必需

- **微信公众号凭证**（二选一）：
  1. `~/.config/wechat-mp-auto/config.json` 中配置 `app_id` 和 `app_secret`
  2. 或在 `~/.openclaw/.env` 中配置环境变量 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`
- **IP 白名单**：确保运行环境的出口 IP 已加入微信公众号后台的白名单

### 可选

- **图片来源**（二选一）：
  - `PEXELS_API_KEY`：Pexels 图库（每月 200 请求，优先横图）
  - `UNSPLASH_API_KEY`：Unsplash 图库（每月 50 请求，优先横图）
  - 图片下载后自动压缩：封面最大 900×500，插图最大 900×400，统一转 JPEG 85% 质量
  - 环境变量或 `~/.openclaw/.env` 中配置

---

## 目录结构

```
wechat-mp-auto/
├── SKILL.md                    # 本文档（AI 编排指南）
├── metadata.json                # Skill 元数据
├── _meta.json                  # ClawHub 元数据
├── README.md                    # 人类使用说明
├── requirements.txt            # Python 依赖
├── src/
│   ├── config.py              # 配置管理
│   ├── token_manager.py       # 微信 Access Token 管理
│   ├── exceptions.py         # 异常定义
│   └── skills/
│       ├── topic_research.py  # 调研工具（research_topic / generate_outline）
│       ├── article_writer.py  # 格式转换工具（convert_to_html）
│       ├── image_generator.py # 图片工具（search_image / generate_image）
│       ├── material_skill.py  # 图片上传工具（upload_image）
│       ├── draft_skill.py     # 草稿推送工具（create_draft）
│       ├── base_skill.py      # 基础类
│       ├── content_reviewer.py # 内容审核
│       └── ...                # 其他辅助模块
└── themes/                    # HTML 主题配色
    ├── default.yaml
    ├── macaron.yaml
    ├── shuimo.yaml
    ├── wenyan.yaml
    └── houge.yaml
```

---

## 安全规范

- Skill 代码中不存储任何凭证
- 日志中自动脱敏（密钥前 4 位 + ... + 后 4 位）
- 所有凭证从配置文件或环境变量读取，不硬编码

---

## 接口权限说明

以下是部分接口对公众号类型的要求：

| 接口/功能 | 权限要求 |
|-----------|---------|
| 素材管理（上传/下载图片） | 普通订阅号即可 |
| 草稿箱管理 | 普通订阅号即可 |
| 文章数据统计（阅读量/点赞/转发等） | 服务号或已认证的订阅号可查询，普通订阅号调用返回 404 |
| 用户管理（获取用户信息） | 普通订阅号即可（部分接口受限） |
| 群发/模板消息 | 需服务号或已认证订阅号 |

> **注意**：如需使用文章数据分析功能，请将公众号升级为服务号或完成认证。
