#!/usr/bin/env python3
"""端到端测试：验证 write_article 处理 AI 内容"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.skills.article_writer import ArticleWriterSkill
import re

writer = ArticleWriterSkill()

# 模拟 AI 生成的文章内容（包含真实的多级标题和表格）
ai_content = """# OpenClaw 安装教程：5分钟搭建你的专属AI助手网关

## 前言

OpenClaw 是一款开源的本地 AI 助理网关，支持接入微信、Telegram、Discord、飞书等 20+ 消息渠道，让你在熟悉的应用里直接和 AI 对话。

## 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | macOS 12 / Ubuntu 20.04 / Windows 11 | macOS 14 / Ubuntu 22.04 |
| Node.js | 18.0+ | 20 LTS+ |
| 内存 | 4GB | 8GB+ |
| 存储 | 5GB 可用空间 | 10GB+ |

#### 不同平台的特殊要求
- **macOS**: 推荐使用 Apple Silicon，性能更佳
- **Linux**: 需要 systemd 支持
- **Windows**: 必须开启 WSL2

## 安装步骤

### 方式一：安装脚本（推荐）

```bash
curl -fsSL https://openclaw.ai/install.sh | sh
```

### 方式二：npm/pnpm

```bash
npm install -g openclaw
# 或
pnpm add -g openclaw
```

### 方式三：Docker

```bash
docker pull openclaw/openclaw:latest
docker run -d -p 3000:3000 openclaw/openclaw
```

## 初始化配置

首次安装完成后，运行以下命令进行初始化配置：

```bash
openclaw init
```

按照提示完成：
1. AI 模型选择
2. 默认渠道配置
3. 管理账户设置

## 常见问题

#### Q1: 安装失败怎么办？
请检查 Node.js 版本是否满足要求，以及网络连接是否正常。

#### Q2: 如何更新到最新版本？
```bash
openclaw update
```

## 总结

本文详细介绍了 OpenClaw 在各平台的安装方法，包括安装脚本、npm、Docker 等多种方式，并提供了初始化配置和常见问题的解决方案。
"""

cover_url = "http://mmbiz.qpic.cn/mmbiz_jpg/BX5mbEgdCNX2rgv7cover.jpg"
section_urls = {
    "前言": "http://mmbiz.qpic.cn/mmbiz_jpg/s1.jpg",
    "系统要求": "http://mmbiz.qpic.cn/mmbiz_jpg/s2.jpg",
    "安装步骤": "http://mmbiz.qpic.cn/mmbiz_jpg/s3.jpg",
    "初始化配置": "http://mmbiz.qpic.cn/mmbiz_jpg/s4.jpg",
    "常见问题": "http://mmbiz.qpic.cn/mmbiz_jpg/s5.jpg",
    "总结": "http://mmbiz.qpic.cn/mmbiz_jpg/s6.jpg",
}

outline = {"title": "OpenClaw 安装教程", "sections": []}

# ========== 模拟 write_article 的 content 处理逻辑 ==========
markdown = ai_content.strip()

# 插入封面图
title_match = re.search(r'^(#{1,6}\s+.+?\n)', markdown, re.MULTILINE)
if title_match:
    pos = title_match.end()
    markdown = markdown[:pos] + f'\n![封面]({cover_url})\n' + markdown[pos:]

# 插入章节图
for section_name, section_url in section_urls.items():
    pattern = r'^(\#{2,3}\s+' + re.escape(section_name) + r'\s*?\n)'
    replacement = r'\1' + f'\n![{section_name}]({section_url})\n'
    markdown = re.sub(pattern, replacement, markdown, flags=re.MULTILINE)

# 转 HTML
html = writer.convert_to_html(markdown, "houge")

# ========== 验证结果 ==========
print("=== Markdown 验证 ===")
print(f"总字符数: {len(markdown)}")
print(f"'## 前言' 出现次数: {markdown.count('## 前言')}")
print(f"'## 系统要求' 出现次数: {markdown.count('## 系统要求')}")
print(f"'####' 在 markdown 中存在: {'####' in markdown}")

print("\n=== HTML 验证 ===")
print(f"#### 转为 h4: {'<h4' in html and '不同平台的特殊要求' in html}")
print(f"表格存在: {'<table' in html}")
print(f"h2 数量: {html.count('<h2')}")
print(f"图片数量: {html.count('<img')}")

# 检查重复问题
print("\n=== 重复标题检查 ===")
h2_titles = re.findall(r'<h2[^>]*>([^<]+)</h2>', html)
print(f"所有 h2 标题: {h2_titles}")
print(f"是否有重复: {len(h2_titles) != len(set(h2_titles))}")

# 检查图片 URL 是否正确
imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', html)
print(f"\n图片 URL 示例:")
for i, url in enumerate(imgs[:3]):
    print(f"  {i+1}. {url[:60]}...")
