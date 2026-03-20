#!/usr/bin/env python3
"""
微信公众号文章批量生成脚本 - 完整版
每篇文章：调研 → 大纲 → 配图 → AI写作 → 推送草稿箱
"""

import sys
import os
import time
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from token_manager import TokenManager
from config import Config


def call_ai_write(topic, outline, research_data):
    """调用AI生成文章内容"""
    sections_text = []
    for s in outline.get("sections", []):
        name = s.get("name", "")
        desc = s.get("description", "")
        key_points = s.get("key_points", [])
        kp_str = ", ".join(key_points) if key_points else "相关要点"
        sections_text.append(f"## {name}\n\n描述：{desc}\n\n关键点：{kp_str}")
    
    sections_md = "\n\n".join(sections_text)
    
    search_snippets = []
    for r in research_data.get("search_results", [])[:5]:
        snippet = r.get("snippet", "")
        if snippet:
            search_snippets.append(snippet)
    
    context = "\n\n".join(search_snippets) if search_snippets else "暂无搜索结果"
    
    prompt = f"""请为微信公众号撰写一篇详尽的文章。

## 主题
{topic}

## 大纲
{sections_md}

## 调研资料
{context}

## 要求
1. 每章节至少300字，内容详尽有深度
2. 使用自然的中文语言风格
3. 包含具体案例、数据或操作步骤（视主题而定）
4. 使用Markdown格式，章节用 ## 标题
5. 封面图位置用 ![封面](cover_image_url)
6. 章节插图位置用 ![章节名](section_image_url)
7. 代码块用 ```language ``` 格式
8. 重点词语用 **加粗**
9. 不要使用HTML标签
10. 直接输出文章内容，不需要额外说明

## 文章内容
"""

    # 使用 openclaw 的 oracle 命令或直接调用
    # 先尝试用 curl 调用本地 openclaw 网关
    try:
        result = subprocess.run(
            ["openclaw", "ai", "--model", "glm-5", "--json", prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except Exception as e:
        print(f"    AI调用方式1失败: {e}")
    
    # 尝试方式2：用 python 调用 OpenAI 兼容接口
    try:
        from openai import OpenAI
        # 读取 API key
        api_keys_file = Path.home() / ".openclaw/credentials/api-keys.json"
        if api_keys_file.exists():
            with open(api_keys_file) as f:
                keys = json.load(f)
                # 尝试找 OpenRouter 或其他兼容 key
                for k, v in keys.items():
                    if v and len(v) > 20:
                        client = OpenAI(
                            api_key=v,
                            base_url="https://openrouter.ai/api/v1"
                        )
                        resp = client.chat.completions.create(
                            model="google/gemini-2.5-flash-lite-preview-06-17",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=4000
                        )
                        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"    AI调用方式2失败: {e}")
    
    return None


def main():
    print("=" * 70)
    print("微信公众号文章批量生成 - 完整版")
    print("=" * 70)

    # 初始化
    config = Config()
    config.set_image_source_preference("search")
    app_id, app_secret = config.get_credentials()
    print(f"\n微信AppID: {app_id[:10]}...")

    token_mgr = TokenManager(app_id, app_secret)
    material = MaterialSkill(token_mgr)
    draft = DraftSkill(token_mgr)
    img_gen = ImageGeneratorSkill()
    writer = ArticleWriterSkill()
    research = TopicResearchSkill()

    # 文章列表
    articles = [
        {
            "topic": "AI大模型在职场办公中的实际应用",
            "template": "macaron",
            "description": "AI大模型在职场办公中的实际应用"
        },
        {
            "topic": "程序员效率提升工具推荐",
            "template": "shuimo",
            "description": "程序员效率提升工具推荐"
        },
        {
            "topic": "个人知识管理体系搭建指南",
            "template": "wenyan",
            "description": "个人知识管理体系搭建指南"
        },
    ]

    results = []

    for i, art in enumerate(articles, 1):
        topic = art["topic"]
        tmpl = art["template"]
        print(f"\n{'='*60}")
        print(f"第{i}篇: {topic} (模板: {tmpl})")
        print(f"{'='*60}")

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
            print(f"    - {s.get('name')}: {s.get('description', '')[:30]}")

        # 3. 封面图
        print(f"\n[3/5] 生成封面图...")
        cover_result = img_gen.generate_and_upload(topic, [], material, "cover")
        cover_url = cover_result.get("wechat_url") if cover_result else None
        cover_local = cover_result.get("local_path") if cover_result else None
        print(f"  封面: {'成功' if cover_url else '失败'}")

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
                print(f"    成功")
            else:
                print(f"    失败")

        # 5. AI写作
        print(f"\n[5/5] AI生成文章内容...")
        md_content = call_ai_write(topic, outline, res)
        if md_content:
            print(f"  AI内容生成成功，字数: {len(md_content)}")
        else:
            print(f"  AI内容生成失败，使用备选方案")
            md_content = None

        # 写作（使用write_article处理图片和HTML转换）
        article = writer.write_article(
            topic=topic,
            outline=outline,
            generate_images=False,  # 图片已手动生成
            template={"type": "local", "id": tmpl},
            cover_image=cover_url,
            section_images=section_imgs,
            content=md_content  # 传入AI生成的内容
        )

        word_count = article.get("word_count", 0)
        print(f"  最终文章字数: {word_count}")

        # 封面上传（缩略图）
        thumb_id = None
        if cover_local:
            print(f"  上传缩略图...")
            r = material.upload_thumb(cover_local)
            thumb_id = r.get("media_id") if r else None
            print(f"  缩略图: {thumb_id[:20] + '...' if thumb_id else '失败'}")

        # 发布草稿
        print(f"  推送到草稿箱...")
        draft_result = draft.create_draft([{
            "title": article.get("title"),
            "author": "贾维斯",
            "content": article.get("html"),
            "thumb_media_id": thumb_id,
            "content_source_url": "https://openclaw.ai"
        }])

        draft_id = draft_result.get("media_id") if draft_result else None
        status = "成功" if draft_id else "失败"

        results.append({
            "title": article.get("title"),
            "template": tmpl,
            "word_count": word_count,
            "cover_images": 1,
            "section_images": len(section_imgs),
            "draft_id": draft_id,
            "status": status
        })

        print(f"\n  === 结果 ===")
        print(f"  标题: {article.get('title')}")
        print(f"  模板: {tmpl}")
        print(f"  配图: {1}封面 + {len(section_imgs)}章节图 = {1 + len(section_imgs)}张")
        print(f"  字数: {word_count}")
        print(f"  草稿箱: {status} (ID: {draft_id or '无'})")

        time.sleep(2)

    # 汇总
    print(f"\n{'='*70}")
    print("批量生成汇总")
    print(f"{'='*70}")
    for r in results:
        print(f"\n标题: {r['title']}")
        print(f"模板: {r['template']}")
        print(f"配图: {r['cover_images'] + r['section_images']}张 (封面{r['cover_images']} + 章节{r['section_images']})")
        print(f"字数: {r['word_count']}")
        print(f"草稿箱: {r['status']} (ID: {r['draft_id'] or '无'})")
        print(f"---")


if __name__ == "__main__":
    main()
