#!/usr/bin/env python3
"""
完整流程测试 - 调试版本
直接生成一篇测试文章，打印完整markdown和HTML用于排查问题
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from token_manager import TokenManager
from config import Config

print("=" * 60)
print("完整流程测试（调试版）")
print("=" * 60)

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
writer = ArticleWriterSkill()
draft = DraftSkill(token_mgr)

# 模拟 AI 生成的文章内容（用于测试 content 参数）
ai_content = """# OpenClaw 安装教程：5分钟搭建你的专属AI助手网关

## 前言

OpenClaw 是一款开源的本地 AI 助理网关，支持接入微信、Telegram、Discord、飞书等 20+ 消息渠道。

## 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | macOS 12 | macOS 14+ |
| Node.js | 18.0+ | 20 LTS+ |
| 内存 | 4GB | 8GB+ |

#### 不同平台说明
- **macOS**: 推荐 Apple Silicon
- **Linux**: 需要 systemd
- **Windows**: 必须开启 WSL2

## 安装步骤

### 方式一：安装脚本

```bash
curl -fsSL https://openclaw.ai/install.sh | sh
```

### 方式二：npm

```bash
npm install -g openclaw
```

## 总结

本文介绍了 OpenClaw 的安装方法。
"""

outline = {
    "title": "OpenClaw 安装教程",
    "sections": [
        {"name": "前言", "key_points": []},
        {"name": "系统要求", "key_points": []},
        {"name": "安装步骤", "key_points": []},
        {"name": "总结", "key_points": []},
    ]
}

# 生成配图
print("\n[1] 生成配图...")
img_gen = ImageGeneratorSkill()
cover_result = img_gen.generate_and_upload("OpenClaw 安装教程", [], material, "cover")
cover_url = cover_result.get("wechat_url")
print(f"  封面: {cover_url[:50] if cover_url else '失败'}...")

section_imgs = {}
for s in outline["sections"]:
    r = img_gen.generate_and_upload(s["name"], [], material, "illustration")
    url = r.get("wechat_url")
    if url:
        section_imgs[s["name"]] = url
        print(f"  章节图-{s['name']}: 成功")
    else:
        print(f"  章节图-{s['name']}: 失败")

# 调用 write_article，传递 content 参数
print("\n[2] 生成文章（使用 content 参数）...")
article = writer.write_article(
    topic="OpenClaw 安装教程",
    outline=outline,
    generate_images=False,
    template={"type": "local", "id": "houge"},
    cover_image=cover_url,
    section_images=section_imgs,
    content=ai_content  # 关键：传递 AI 生成的内容
)

print(f"\n[3] 文章结果:")
print(f"  标题: {article.get('title')}")
print(f"  字数: {article.get('word_count')}")
print(f"  markdown长度: {len(article.get('markdown', ''))}")
print(f"  html长度: {len(article.get('html', ''))}")

# 打印 markdown 内容用于排查
print("\n[4] === Markdown 内容（用于排查重复标题问题）===")
print(article.get("markdown", "")[:3000])

# 打印 HTML 片段
print("\n[5] === HTML 片段（前2000字符）===")
print(article.get("html", "")[:2000])

# 发布到草稿箱
print("\n[6] 发布到草稿箱...")
if cover_url:
    try:
        thumb_r = material.upload_thumb(cover_url)
        thumb_id = thumb_r.get("media_id") if thumb_r else None
        print(f"  缩略图: {thumb_id or '失败'}")
    except Exception as e:
        print(f"  缩略图失败: {e}")
        thumb_id = None
else:
    thumb_id = None

draft_r = draft.create_draft([{
    "title": article.get("title"),
    "author": "贾维斯",
    "content": article.get("html"),
    "thumb_media_id": thumb_id,
    "content_source_url": "https://openclaw.ai"
}])
print(f"  草稿: {'成功 ' + str(draft_r.get('media_id')) if draft_r else '失败'}")

print("\n完成！")
