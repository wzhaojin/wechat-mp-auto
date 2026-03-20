#!/usr/bin/env python3
"""完整版全流程测试 - 包含真实图片上传"""

import sys
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
print("完整版全流程测试（带图片上传）")
print("=" * 60)

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
print("AppID: %s..." % app_id[:10])

# 设置图片来源为搜索
config.set_image_source_preference("search")

token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
draft = DraftSkill(token_mgr)
img_gen = ImageGeneratorSkill()
writer = ArticleWriterSkill()
research = TopicResearchSkill()
reviewer = ContentReviewerSkill()


def gen_cover_and_upload(img_gen, material, title):
    """生成并上传封面"""
    print("  [封面] 生成...")
    try:
        r = img_gen.generate_and_upload(title, [], material, "cover")
        url = r.get("wechat_url")
        if url:
            print("  [封面] 成功: %s..." % url[:40])
            return url
    except Exception as e:
        print("  [封面] 失败: %s" % e)
    return None


def gen_section_images(img_gen, material, outline):
    """生成章节图片"""
    imgs = {}
    for s in outline.get("sections", []):
        name = s.get("name", "")
        print("  [章节图-%s] 生成..." % name)
        try:
            r = img_gen.generate_and_upload(name, [], material, "illustration")
            url = r.get("wechat_url")
            if url:
                imgs[name] = url
                print("  [章节图-%s] 成功" % name)
        except Exception as e:
            print("  [章节图-%s] 失败: %s" % (name, e))
    return imgs


def publish_article(topic, outline, tmpl_id):
    """发布文章"""
    # 1. 写作
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,  # 图片已单独处理
        template={"type": "local", "id": tmpl_id}
    )
    
    # 2. 审核
    rev = reviewer.review_article({
        "markdown": article.get("markdown", ""),
        "content": article.get("html", "")
    })
    
    # 3. 发布
    draft_r = draft.create_draft([{
        "title": article.get("title"),
        "author": "贾维斯",
        "content": article.get("html"),
        "content_source_url": "https://openclaw.ai"
    }])
    
    return {
        "title": article.get("title"),
        "template": tmpl_id,
        "draft_id": draft_r.get("media_id") if draft_r else None,
        "review_passed": rev.get("passed", False)
    }


# ===== 测试1: 单篇（侯哥） =====
print("\n" + "=" * 50)
print("测试1: OpenClaw安装教程（侯哥）")
print("=" * 50)

# 调研
print("\n[1] 调研...")
res = research.research_topic("OpenClaw 安装教程")
print(" 搜索: %d条" % len(res.get("search_results", [])))

# 大纲
print("\n[2] 大纲...")
outline = research.generate_outline("OpenClaw 安装教程", res)
print(" 章节: %d个" % len(outline.get("sections", [])))

# 封面图
print("\n[3] 封面图...")
cover_url = gen_cover_and_upload(img_gen, material, "OpenClaw 安装教程")

# 章节图
print("\n[4] 章节图...")
section_imgs = gen_section_images(img_gen, material, outline)

# 写入文章（用已上传的图片URL）
print("\n[5] 组装文章...")
article = writer.write_article(
    topic="OpenClaw 安装教程",
    outline=outline,
    generate_images=False,
    template={"type": "local", "id": "houge"},
    cover_image=cover_url,  # 用已上传的URL
    section_images=section_imgs
)
print(" 标题: %s" % article.get("title"))
print(" 模板: %s" % article.get("theme"))

# 发布
print("\n[6] 发布...")
draft_r = draft.create_draft([{
    "title": article.get("title"),
    "author": "贾维斯",
    "content": article.get("html"),
    "content_source_url": "https://openclaw.ai"
}])
draft_id = draft_r.get("media_id") if draft_r else None
print(" 草稿ID: %s" % (draft_id or "失败"))


# ===== 测试2: 批量3篇 =====
print("\n" + "=" * 50)
print("测试2: 批量3篇")
print("=" * 50)

batch = [
    ("微信公众号运营技巧", "macaron"),
    ("AI工具在内容创作中的应用", "shuimo"),
    ("Markdown写作最佳实践", "wenyan"),
]

for i, (topic, tmpl) in enumerate(batch, 1):
    print("\n[批量-%d] %s (%s)" % (i, topic, tmpl))
    
    # 调研
    res = research.research_topic(topic)
    outline = research.generate_outline(topic, res)
    
    # 封面
    cover = gen_cover_and_upload(img_gen, material, topic)
    
    # 章节
    secs = gen_section_images(img_gen, material, outline)
    
    # 写作
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,
        template={"type": "local", "id": tmpl},
        cover_image=cover,
        section_images=secs
    )
    
    # 发布
    draft_r = draft.create_draft([{
        "title": article.get("title"),
        "author": "贾维斯",
        "content": article.get("html"),
        "content_source_url": "https://openclaw.ai"
    }])
    draft_id = draft_r.get("media_id") if draft_r else None
    print("  草稿: %s" % (draft_id or "失败"))

print("\n" + "=" * 60)
print("完成")
print("=" * 60)
