#!/usr/bin/env python3
"""
OpenClaw安装教程微信公众号文章生成脚本
主题：OpenClaw安装教程
模板：猴哥风格（houge）
"""

import sys
import os
import time
import subprocess
import json
from pathlib import Path

# 设置PYTHONPATH
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir / "src"))
os.environ['PYTHONPATH'] = str(script_dir / "src")

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from token_manager import TokenManager
from config import Config


def call_ai_write(topic, outline, research_data):
    """调用AI生成文章内容 - 使用阿里云百炼API"""
    import requests
    
    sections = outline.get("sections", [])
    
    # 构建详细的大纲文本
    sections_text = []
    for i, s in enumerate(sections, 1):
        name = s.get("name", "")
        desc = s.get("description", "")
        key_points = s.get("key_points", [])
        kp_str = "\n".join([f"    - {kp}" for kp in key_points]) if key_points else ""
        sections_text.append(f"## 第{i}章: {name}\n\n描述：{desc}\n\n关键点：\n{kp_str}")
    
    sections_md = "\n\n".join(sections_text)
    
    # 调研资料
    search_context = []
    for r in research_data.get("search_results", [])[:8]:
        snippet = r.get("snippet", "")
        title = r.get("title", "")
        if snippet:
            search_context.append(f"【{title}】\n{snippet}")
    context_text = "\n\n".join(search_context) if search_context else "暂无相关资料"
    
    prompt = f"""你是一位专业的微信公众号作者。请根据以下大纲和调研资料，撰写一篇详尽、专业的微信公众号文章。

## 文章主题
{topic}

## 文章大纲
{sections_md}

## 调研资料
{context_text}

## 写作要求
1. **结构**: 严格按照给定的大纲章节来组织内容
2. **字数**: 每个章节至少500字，内容详尽深入
3. **语言风格**: 口语化、专业、有温度，像和读者聊天
4. **格式**: 使用Markdown格式
5. **重点强调**: 使用 **加粗** 强调关键词汇和命令
6. **代码**: 使用 ```bash 或 ``` 包裹命令行代码
7. **表格**: 使用 Markdown 表格展示对比信息（如系统要求对比、安装方式对比等）
8. **图片占位符**: 
   - 封面图位置用 ![封面](cover_image_url)
   - 章节插图位置用 ![章节名](section_image_url)
9. **禁止**: 不使用HTML标签、不使用斜体语法
10. **直接输出**: 只输出文章内容，不要任何额外说明

## 文章内容
"""

    # 使用阿里云百炼API
    API_KEY = "sk-2e68ec6ceb8b4b168b0fca077993e038"
    API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-long",
        "input": {"prompt": prompt},
        "parameters": {"max_tokens": 8000, "temperature": 0.7}
    }
    
    try:
        resp = requests.post(API_URL, headers=headers, json=data, timeout=300)
        if resp.status_code == 200:
            result = resp.json()
            choices = result.get("output", {}).get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return content
            content = result.get("output", {}).get("text", "")
            return content
        else:
            print(f"    API错误: {resp.status_code} - {resp.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"    请求超时")
    except Exception as e:
        print(f"    请求异常: {e}")
    
    return None


def main():
    print("=" * 70)
    print("OpenClaw安装教程 - 微信公众号文章生成")
    print("=" * 70)

    # 初始化
    config = Config()
    config.set_image_source_preference("search")  # 使用图片搜索
    app_id, app_secret = config.get_credentials()
    print(f"\n微信AppID: {app_id[:10]}...")

    token_mgr = TokenManager(app_id, app_secret)
    material = MaterialSkill(token_mgr)
    draft = DraftSkill(token_mgr)
    img_gen = ImageGeneratorSkill()
    writer = ArticleWriterSkill()
    research = TopicResearchSkill()

    topic = "OpenClaw安装教程：从零开始搭建你的AI助手网关"
    tmpl = "houge"  # 猴哥模板

    print(f"\n主题: {topic}")
    print(f"模板: {tmpl}")

    # 1. 调研
    print(f"\n[1/5] 选题调研...")
    res = research.research_topic(topic)
    search_count = len(res.get("search_results", []))
    print(f"  搜索结果: {search_count} 条")

    # 2. 大纲
    print(f"\n[2/5] 生成大纲...")
    outline = research.generate_outline(topic, res)
    sections = outline.get("sections", [])
    print(f"  标题: {outline.get('title')}")
    print(f"  章节数: {len(sections)}")
    for s in sections:
        print(f"    - {s.get('name')}: {s.get('description', '')[:40]}...")

    # 3. 封面图
    print(f"\n[3/5] 生成封面图...")
    cover_result = img_gen.generate_and_upload(topic, [], material, "cover")
    cover_url = cover_result.get("wechat_url") if cover_result else None
    cover_local = cover_result.get("local_path") if cover_result else None
    print(f"  封面: {'成功' if cover_url else '失败'}")
    if cover_url:
        print(f"  封面URL: {cover_url[:50]}...")

    # 4. 章节图
    print(f"\n[4/5] 生成章节图...")
    section_imgs = {}
    for s in sections:
        sname = s.get("name", "")
        print(f"  正在生成: {sname}...")
        r = img_gen.generate_and_upload(sname, [], material, "illustration")
        url = r.get("wechat_url") if r else None
        if url:
            section_imgs[sname] = url
            print(f"    成功: {url[:50]}...")
        else:
            print(f"    失败，跳过")

    # 5. AI写作
    print(f"\n[5/5] AI生成文章内容...")
    md_content = call_ai_write(topic, outline, res)
    if md_content:
        print(f"  AI内容生成成功，字数: {len(md_content)}")
    else:
        print(f"  AI内容生成失败")
        return

    # 写作（处理图片和HTML转换）
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,  # 图片已手动生成
        template={"type": "local", "id": tmpl},
        cover_image=cover_url,
        section_images=section_imgs,
        content=md_content
    )

    word_count = article.get("word_count", 0)
    html_content = article.get("html", "")
    final_title = article.get("title", topic)
    print(f"  最终文章字数: {word_count}")
    print(f"  HTML长度: {len(html_content)}")

    # 封面上传（缩略图）
    thumb_id = None
    if cover_local:
        print(f"\n  上传缩略图...")
        r = material.upload_thumb(cover_local)
        thumb_id = r.get("media_id") if r else None
        if thumb_id:
            print(f"  缩略图成功: {thumb_id[:20]}...")
        else:
            print(f"  缩略图失败")

    # 发布草稿
    print(f"\n  推送到草稿箱...")
    draft_result = draft.create_draft([{
        "title": final_title,
        "author": "贾维斯",
        "content": html_content,
        "thumb_media_id": thumb_id,
        "content_source_url": "https://docs.openclaw.ai/"
    }])

    draft_id = draft_result.get("media_id") if draft_result else None
    
    # 汇总
    print(f"\n{'='*70}")
    print("生成结果汇总")
    print(f"{'='*70}")
    print(f"标题: {final_title}")
    print(f"模板: {tmpl}")
    print(f"配图: {1 if cover_url else 0}封面 + {len(section_imgs)}章节图")
    print(f"字数: {word_count}")
    print(f"草稿箱: {'成功' if draft_id else '失败'}")
    if draft_id:
        print(f"草稿ID: {draft_id}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
