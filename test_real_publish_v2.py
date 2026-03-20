#!/usr/bin/env python3
"""
全流程真实发布测试 - 修复版
解决: 1) AI内容未传递给write_article 2) 缩略图用URL而非本地路径
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.image_generator import ImageGeneratorSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from skills.content_reviewer import ContentReviewerSkill
from token_manager import TokenManager
from config import Config

print("=" * 60)
print("全流程真实发布测试（修复版）")
print("=" * 60)

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
draft = DraftSkill(token_mgr)
img_gen = ImageGeneratorSkill()
writer = ArticleWriterSkill()
reviewer = ContentReviewerSkill()

# 从文件读取 AI 内容
AI_ARTICLE_CONTENT = Path("/Users/wzj/.openclaw/workspace/test_content.md").read_text()
print(f"AI内容长度: {len(AI_ARTICLE_CONTENT)} 字符")


def generate_all_images(img_gen, material, topic, outline):
    """生成封面和章节图"""
    cover_path = None
    cover_url = None
    section_imgs = {}

    print("  [封面] 生成中...")
    try:
        r = img_gen.generate_and_upload(topic, [], material, "cover")
        cover_path = r.get("local_path")
        cover_url = r.get("wechat_url")
        if cover_url:
            print(f"  [封面] 成功: {cover_url[:50]}...")
        else:
            print(f"  [封面] 失败（无 wechat_url）")
    except Exception as e:
        print(f"  [封面] 异常: {e}")

    for s in outline.get("sections", []):
        name = s.get("name", "")
        print(f"  [章节图-{name}] 生成中...")
        try:
            r = img_gen.generate_and_upload(name, [], material, "illustration")
            url = r.get("wechat_url")
            if url:
                section_imgs[name] = url
                print(f"  [章节图-{name}] 成功")
            else:
                print(f"  [章节图-{name}] 失败（无 wechat_url）")
        except Exception as e:
            print(f"  [章节图-{name}] 异常: {e}")

    return cover_path, cover_url, section_imgs


def publish_article(topic, outline, tmpl_id, cover_path, cover_url, section_imgs, ai_content=None):
    """发布文章到草稿箱"""
    print("  [write_article] 调用...")
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,
        template={"type": "local", "id": tmpl_id},
        cover_image=cover_url,
        section_images=section_imgs,
        content=ai_content  # 关键：传递 AI 生成的内容
    )
    print(f"  [write_article] 完成: markdown={len(article.get('markdown',''))}字符, html={len(article.get('html',''))}字符")

    # 审核
    review = reviewer.review_article({
        "markdown": article.get("markdown", ""),
        "content": article.get("html", "")
    })
    print(f"  [审核] 通过: {review.get('passed')}, 重复度: {review.get('plagiarism',{}).get('similarity',0)}%")

    # 缩略图：需要本地文件路径，不接受 URL
    thumb_id = None
    if cover_path and Path(cover_path).exists():
        try:
            thumb_r = material.upload_thumb(cover_path)
            thumb_id = thumb_r.get("media_id")
            print(f"  [缩略图] 成功: {str(thumb_id)[:30]}...")
        except Exception as e:
            print(f"  [缩略图] 失败: {e}")
    else:
        print(f"  [缩略图] 跳过（无本地路径）")

    # 发布草稿
    draft_r = None
    try:
        draft_r = draft.create_draft([{
            "title": article.get("title"),
            "author": "贾维斯",
            "content": article.get("html"),
            "thumb_media_id": thumb_id,
            "content_source_url": "https://openclaw.ai"
        }])
        print(f"  [草稿] 成功: {draft_r.get('media_id') if draft_r else '失败'}")
    except Exception as e:
        print(f"  [草稿] 失败: {e}")

    return {
        "title": article.get("title"),
        "template": tmpl_id,
        "words": article.get("word_count", 0),
        "markdown_chars": len(article.get("markdown", "")),
        "html_chars": len(article.get("html", "")),
        "cover": cover_url,
        "sections": len(section_imgs),
        "draft_id": draft_r.get("media_id") if draft_r else None,
        "review_passed": review.get("passed", False),
        "plagiarism": review.get("plagiarism", {}).get("similarity", 0),
        "markdown": article.get("markdown", ""),
        "html": article.get("html", ""),
    }


# ===== 测试 =====
print("\n" + "=" * 60)
print("测试: OpenClaw安装教程（侯哥主题）")
print("=" * 60)

try:
    print("\n[1] 选题调研...")
    research = TopicResearchSkill()
    res = research.research_topic("OpenClaw 安装教程")
    print(f"  搜索: {len(res.get('search_results', []))} 条")

    print("\n[2] 生成大纲...")
    outline = research.generate_outline("OpenClaw 安装教程", res)
    print(f"  标题: {outline.get('title')}")
    print(f"  章节: {len(outline.get('sections', []))} 个")

    print("\n[3] 生成配图...")
    cover_path, cover_url, section_imgs = generate_all_images(
        img_gen, material, "OpenClaw 安装教程", outline
    )

    print("\n[4] 发布到草稿箱...")
    result = publish_article(
        "OpenClaw 安装教程", outline, "houge",
        cover_path, cover_url, section_imgs,
        ai_content=AI_ARTICLE_CONTENT
    )

    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"  标题: {result['title']}")
    print(f"  字数: {result['words']}")
    print(f"  markdown: {result['markdown_chars']} 字符")
    print(f"  html: {result['html_chars']} 字符")
    print(f"  草稿ID: {result['draft_id'] or '失败'}")
    print(f"  审核: {'通过' if result['review_passed'] else '失败'}")
    
    print("\n=== Markdown 内容（用于排查）===")
    print(result["markdown"][:1500])

except Exception as e:
    print(f"\n[FAIL] 测试失败: {e}")
    import traceback
    traceback.print_exc()