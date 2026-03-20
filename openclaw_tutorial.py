#!/usr/bin/env python3
"""
OpenClaw 安装教程 - 微信公众号文章生成脚本
使用 houge 模板，推送到草稿箱
"""

import sys
import os
import time
import json
import re
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from token_manager import TokenManager
from config import Config


# 阿里云百炼 API 配置
DASHSCOPE_API_KEY = "sk-2e68ec6ceb8b4b168b0fca077993e038"
DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"


def call_bailian_ai(prompt, model="qwen-long", max_tokens=4000):
    """调用阿里云百炼API生成内容"""
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {"max_tokens": max_tokens, "temperature": 0.7}
    }
    try:
        resp = requests.post(DASHSCOPE_API_URL, headers=headers, json=data, timeout=180)
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
            return None
    except requests.exceptions.Timeout:
        print(f"    请求超时")
        return None
    except Exception as e:
        print(f"    请求异常: {e}")
        return None


def generate_article_content(topic, outline, research_data):
    """调用AI生成完整文章内容"""
    sections = outline.get("sections", [])
    
    # 构建大纲文本
    sections_md = []
    for i, s in enumerate(sections, 1):
        name = s.get("name", "")
        desc = s.get("description", "")
        kps = s.get("key_points", [])
        kp_str = "\n".join([f"  - {kp}" for kp in kps]) if kps else "  - 相关要点"
        sections_md.append(f"**第{i}章: {name}**\n描述: {desc}\n关键要点:\n{kp_str}")
    
    sections_text = "\n\n".join(sections_md)
    
    # 调研资料摘要
    search_context = []
    for r in research_data.get("search_results", [])[:5]:
        snippet = r.get("snippet", "")
        title = r.get("title", "")
        if snippet:
            search_context.append(f"【{title}】\n{snippet}")
    context_text = "\n\n".join(search_context) if search_context else "暂无相关资料（基于作者实际经验编写）"
    
    prompt = f"""你是一位精通 AI 助手开发和 DevOps 的专业技术作者。请根据以下大纲和调研资料，撰写一篇详尽、专业的微信公众号文章，关于 OpenClaw（一个开源 AI 助手框架）的安装教程。

## 文章主题
{topic}

## 文章大纲
{sections_text}

## 调研资料
{context_text}

## 写作要求
1. **结构**: 严格按照给定的大纲章节来组织内容
2. **字数**: 每个章节至少400字，内容详尽深入，包含大量具体的命令、配置示例和踩坑说明
3. **风格**: 使用通俗易懂的中文，段落之间逻辑连贯，适合技术读者
4. **格式**: 
   - 主标题用 # 标题（仅一个#）
   - 章节标题用 ## 二级标题
   - 子章节使用 ### 三级标题
   - 重点词语用 **加粗**
   - 代码块用 ```code ``` 格式（包含真实的命令和配置）
   - 列表用 - 格式
5. **配图标记**: 
   - 封面图位置使用: ![cover](COVER_URL)
   - 每个章节（##标题）后面使用: ![章节名](SECTION_URL)
6. **内容质量**: 
   - 包含具体的安装命令（如 curl、npm、pip 等）
   - 包含真实的配置文件示例（JSON、YAML、.env 等）
   - 有具体的踩坑说明和解决方案
   - 段落丰富，不要过于稀疏
7. **开头**: 文章开头要有吸引力的引入段落，介绍 OpenClaw 的价值
8. **结尾**: 文章结尾要有总结和行动号召（CTA）

请直接输出完整的Markdown文章内容，不需要任何说明：
"""
    
    print(f"    正在调用AI生成文章内容 (max_tokens=8000)...")
    result = call_bailian_ai(prompt, max_tokens=8000)
    
    if result:
        print(f"    AI生成成功，内容长度: {len(result)}字符")
        return result
    else:
        print(f"    AI生成失败")
        return None


def inject_images_to_markdown(md_content, cover_url, section_imgs):
    """将图片URL注入到markdown中"""
    # 封面
    md_content = md_content.replace("![cover](COVER_URL)", f"![封面]({cover_url})" if cover_url else "")
    
    # 章节图 - 尝试多种可能的占位符格式
    for sname, surl in section_imgs.items():
        md_content = md_content.replace(f"![{sname}](SECTION_URL)", f"![{sname}]({surl})")
        md_content = md_content.replace(f"![{sname}](section_image_url)", f"![{sname}]({surl})")
        md_content = md_content.replace(f"![{sname}](section)", f"![{sname}]({surl})")
        md_content = md_content.replace(f"![{sname}](SECTION)", f"![{sname}]({surl})")
        md_content = md_content.replace(f"![{sname}](图片)", f"![{sname}]({surl})")
        md_content = md_content.replace(f"![{sname}](image)", f"![{sname}]({surl})")
    
    return md_content


def main():
    print("=" * 70)
    print("OpenClaw 安装教程 - 微信公众号文章生成")
    print("模板: houge | 图片来源: search")
    print("=" * 70)

    # 初始化
    config = Config()
    config.set_image_source_preference("search")
    app_id, app_secret = config.get_credentials()
    print(f"\n微信AppID: {app_id[:10]}...")
    print(f"图片来源: Pexels/Unsplash搜索")

    token_mgr = TokenManager(app_id, app_secret)
    material = MaterialSkill(token_mgr)
    draft = DraftSkill(token_mgr)
    img_gen = ImageGeneratorSkill()
    writer = ArticleWriterSkill()
    research = TopicResearchSkill()

    topic = "OpenClaw 安装教程"
    template = "houge"

    print(f"\n{'='*60}")
    print(f"文章: {topic}")
    print(f"模板: {template}")
    print(f"{'='*60}")

    try:
        # 1. 选题调研
        print(f"\n[1/7] 选题调研...")
        res = research.research_topic(topic)
        search_count = len(res.get("search_results", []))
        print(f"  → 搜索结果: {search_count} 条")
        for r in res.get("search_results", [])[:3]:
            print(f"    - {r.get('title', '')[:60]}")

        # 2. 生成大纲
        print(f"\n[2/7] 生成大纲...")
        outline = research.generate_outline(topic, res)
        sections = outline.get("sections", [])
        print(f"  → 标题: {outline.get('title')}")
        print(f"  → 章节数: {len(sections)}")
        for s in sections:
            print(f"    - {s.get('name')}")

        # 3. 封面图
        print(f"\n[3/7] 生成封面图...")
        cover_result = img_gen.generate_and_upload(topic, [], material, "cover")
        cover_url = cover_result.get("wechat_url") if cover_result else None
        cover_local = cover_result.get("local_path") if cover_result else None
        print(f"  → 封面: {'✓ ' + str(cover_url)[:50] if cover_url else '✗'}")
        if cover_local:
            print(f"  → 本地路径: {cover_local}")

        # 4. 章节图
        print(f"\n[4/7] 生成章节图...")
        section_imgs = {}
        for s in sections:
            sname = s.get("name", "")
            time.sleep(1)
            r = img_gen.generate_and_upload(sname, [], material, "illustration")
            url = r.get("wechat_url") if r else None
            local = r.get("local_path") if r else None
            if url:
                section_imgs[sname] = url
                print(f"  → {sname}: ✓")
                print(f"    URL: {url[:60]}...")
            else:
                print(f"  → {sname}: ✗ (本地: {local})")

        # 5. AI写作
        print(f"\n[5/7] AI生成文章内容...")
        md_content = generate_article_content(topic, outline, res)
        
        if not md_content:
            print("  → AI生成失败，程序终止")
            return

        # 注入图片URL
        md_content = inject_images_to_markdown(md_content, cover_url, section_imgs)
        print(f"  图片注入完成")

        # 计算字数
        word_count = writer.count_words(md_content)
        print(f"  → Markdown字数: {word_count}")

        # 转换为HTML
        print(f"\n[6/7] 转换为HTML (houge模板)...")
        html_content = writer.convert_to_html(md_content, template)
        print(f"  → HTML转换完成，长度: {len(html_content)}")

        # 封面上传缩略图
        thumb_id = None
        if cover_local:
            print(f"\n  上传缩略图 (thumb_media_id)...")
            time.sleep(1)
            try:
                r = material.upload_thumb(cover_local)
                thumb_id = r.get("media_id") if r else None
                if thumb_id:
                    print(f"  → 缩略图ID: {thumb_id[:30]}...")
                else:
                    print(f"  → 缩略图上传结果: {r}")
            except Exception as e:
                print(f"  → 缩略图上传失败: {e}")
        else:
            print(f"\n  无封面本地路径，跳过缩略图上传")

        # 推送到草稿箱
        print(f"\n[7/7] 推送到草稿箱...")
        article_title = outline.get('title', topic)
        
        draft_result = draft.create_draft([{
            "title": article_title,
            "author": "贾维斯",
            "content": html_content,
            "thumb_media_id": thumb_id,
            "content_source_url": "https://openclaw.ai"
        }])

        draft_id = draft_result.get("media_id") if draft_result else None
        status = "✓成功" if draft_id else "✗失败"

        # 计算HTML中的图片数量
        html_img_count = len(re.findall(r'<img[^>]+>', html_content))

        print(f"\n{'='*60}")
        print(f"  文章标题: {article_title}")
        print(f"  模板: {template}")
        print(f"  配图: {1 if cover_url else 0}封面 + {len(section_imgs)}章节 = {1 + len(section_imgs)}张")
        print(f"  HTML内图片: {html_img_count}张")
        print(f"  Markdown字数: {word_count}")
        print(f"  草稿状态: {status}")
        if draft_id:
            print(f"  草稿ID: {draft_id}")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n  → 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
