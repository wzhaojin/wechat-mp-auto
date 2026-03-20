#!/usr/bin/env python3
"""
全流程真实发布测试
- 文章推送到微信草稿箱
- 使用Pexels/Unsplash真实配图
"""

import sys
import os
import time
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
print("全流程真实发布测试")
print("=" * 60)

# ===== 初始化组件 =====
print("\n[初始化] 检查配置...")
config = Config()
app_id, app_secret = config.get_credentials()
print("  微信AppID: %s..." % app_id[:10])
print("  微信AppSecret: %s..." % app_secret[:10])

# 先设置图片来源为搜索（图省AI生图，因为glm-5不支持）
config.set_image_source_preference("search")
print("  已设置图片来源: search (因glm-5不支持生图)")

token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
draft = DraftSkill(token_mgr)
img_gen = ImageGeneratorSkill()
writer = ArticleWriterSkill()

# 检查图片源
img_opts = img_gen.get_image_source_options()
available = [o["id"] for o in img_opts.get("options", []) if not o.get("disabled")]
print("  可用图片来源: %s" % available)


def generate_all_images(img_gen, material, topic, outline):
    """生成封面和章节图"""
    cover_path = None
    cover_url = None
    section_imgs = {}

    # 封面
    print("  [封面] 生成中...")
    try:
        r = img_gen.generate_and_upload(topic, [], material, "cover")
        cover_path = r.get("local_path")
        cover_url = r.get("wechat_url")
        if cover_url:
            print("  [封面] 成功: %s..." % cover_url[:50])
        else:
            print("  [封面] 失败")
    except Exception as e:
        print("  [封面] 异常: %s" % e)

    # 章节图
    for s in outline.get("sections", []):
        name = s.get("name", "")
        print("  [章节图-%s] 生成中..." % name)
        try:
            r = img_gen.generate_and_upload(name, [], material, "illustration")
            url = r.get("wechat_url")
            if url:
                section_imgs[name] = url
                print("  [章节图-%s] 成功" % name)
            else:
                print("  [章节图-%s] 失败" % name)
        except Exception as e:
            print("  [章节图-%s] 异常: %s" % (name, e))

    return cover_path, cover_url, section_imgs


def publish_article(topic, outline, tmpl_id, cover_url, section_imgs, ai_content=None):
    """发布文章到草稿箱
    
    Args:
        ai_content: AI生成的完整文章内容（Markdown格式），有值时优先使用
    """
    # 写作
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,
        template={"type": "local", "id": tmpl_id},
        cover_image=cover_url,
        section_images=section_imgs,
        content=ai_content  # 传递AI生成的内容
    )

    # 审核
    reviewer = ContentReviewerSkill()
    review = reviewer.review_article({
        "markdown": article.get("markdown", ""),
        "content": article.get("html", "")
    })

    # 上传播封面为缩略图
    thumb_id = None
    if cover_url:
        try:
            thumb_r = material.upload_thumb(cover_url)
            thumb_id = thumb_r.get("media_id") if thumb_r else None
            print("  [缩略图] %s" % (thumb_id or "失败"))
        except Exception as e:
            print("  [缩略图] 失败: %s" % e)

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
        print("  [草稿] 成功, media_id=%s" % (draft_r.get("media_id") if draft_r else "失败"))
    except Exception as e:
        print("  [草稿] 失败: %s" % e)

    return {
        "title": article.get("title"),
        "template": tmpl_id,
        "words": article.get("word_count", 0),
        "cover": cover_url,
        "sections": len(section_imgs),
        "draft_id": draft_r.get("media_id") if draft_r else None,
        "review_passed": review.get("passed", False),
        "plagiarism": review.get("plagiarism", {}).get("similarity", 0)
    }


# ===== 测试1: 单篇（侯哥主题） =====
print("\n" + "=" * 60)
print("测试1: OpenClaw安装教程（侯哥主题）")
print("=" * 60)

try:
    # 调研
    print("\n[1] 选题调研...")
    research = TopicResearchSkill()
    res = research.research_topic("OpenClaw 安装教程")
    print("  搜索: %d 条" % len(res.get("search_results", [])))

    # 大纲
    print("\n[2] 生成大纲...")
    outline = research.generate_outline("OpenClaw 安装教程", res)
    print("  标题: %s" % outline.get("title"))
    print("  章节: %d 个" % len(outline.get("sections", [])))

    # 配图
    print("\n[3] 生成配图...")
    cover_path, cover_url, section_imgs = generate_all_images(
        img_gen, material, "OpenClaw 安装教程", outline
    )

    # 发布
    print("\n[4] 发布到草稿箱...")
    result = publish_article("OpenClaw 安装教程", outline, "houge", cover_url, section_imgs)

    print("\n[结果]")
    print("  标题: %s" % result["title"])
    print("  模板: %s" % result["template"])
    print("  字数: %d" % result["words"])
    print("  封面: %s" % ("有" if result["cover"] else "无"))
    print("  章节图: %d 张" % result["sections"])
    print("  草稿ID: %s" % (result["draft_id"] or "失败"))
    print("  审核: %s (重复度: %.1f%%)" % ("通过" if result["review_passed"] else "失败", result["plagiarism"]))

    print("\n[OK] 测试1完成")

except Exception as e:
    print("\n[FAIL] 测试1失败: %s" % e)
    import traceback
    traceback.print_exc()


# ===== 测试2: 批量3篇 =====
print("\n" + "=" * 60)
print("测试2: 批量3篇文章（各用不同主题）")
print("=" * 60)

batch_topics = [
    ("微信公众号运营技巧", "macaron"),
    ("AI工具在内容创作中的应用", "shuimo"),
    ("Markdown写作最佳实践", "wenyan"),
]

try:
    research = TopicResearchSkill()
    results = []

    for i, (topic, tmpl) in enumerate(batch_topics, 1):
        print("\n[批量-%d] %s (%s)" % (i, topic, tmpl))

        # 调研
        res = research.research_topic(topic)
        print("  搜索: %d 条" % len(res.get("search_results", [])))

        # 大纲
        outline = research.generate_outline(topic, res)
        print("  章节: %d 个" % len(outline.get("sections", [])))

        # 配图
        cover_path, cover_url, section_imgs = generate_all_images(
            img_gen, material, topic, outline
        )

        # 发布
        print("  发布中...")
        result = publish_article(topic, outline, tmpl, cover_url, section_imgs)
        results.append(result)

        print("  草稿ID: %s | 审核: %s" % (
            result["draft_id"] or "失败",
            "通过" if result["review_passed"] else "失败"
        ))

    print("\n" + "-" * 50)
    print("批量结果:")
    for r in results:
        status = "OK" if r["draft_id"] else "FAIL"
        print("  [%s] %s (%s)" % (status, r["title"], r["template"]))
        print("      字数: %d | 章节图: %d | 重复度: %.1f%%" % (
            r["words"], r["sections"], r["plagiarism"]))
        print("      草稿ID: %s" % (r["draft_id"] or "无"))

    print("\n[OK] 测试2完成")

except Exception as e:
    print("\n[FAIL] 测试2失败: %s" % e)
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("全流程测试完成")
print("=" * 60)
