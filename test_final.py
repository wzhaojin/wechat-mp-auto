#!/usr/bin/env python3
"""完整版全流程测试 - 正确使用local_path上传封面"""

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
print("完整版全流程测试")
print("=" * 60)

# 初始化
config = Config()
config.set_image_source_preference("search")
app_id, app_secret = config.get_credentials()
print("AppID: %s..." % app_id[:10])

token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
draft = DraftSkill(token_mgr)
img_gen = ImageGeneratorSkill()
writer = ArticleWriterSkill()
research = TopicResearchSkill()
reviewer = ContentReviewerSkill()


def upload_cover(local_path):
    """上传封面图"""
    print("  [封面上传]...")
    try:
        r = material.upload_thumb(local_path)
        if r and r.get("media_id"):
            print("  [封面上传] 成功: %s" % r["media_id"][:20])
            return r["media_id"]
    except Exception as e:
        print("  [封面上传] 失败: %s" % e)
    return None


# ===== 测试1: 单篇（侯哥） =====
print("\n" + "=" * 50)
print("测试1: OpenClaw安装教程（侯哥）")
print("=" * 50)

# 1. 调研
print("\n[1] 调研...")
res = research.research_topic("OpenClaw 安装教程")
print(" 搜索: %d条" % len(res.get("search_results", [])))

# 2. 大纲
print("\n[2] 大纲...")
outline = research.generate_outline("OpenClaw 安装教程", res)
print(" 章节: %d个" % len(outline.get("sections", [])))

# 3. 封面图
print("\n[3] 封面图...")
r = img_gen.generate_and_upload("OpenClaw 安装教程", [], material, "cover")
cover_local = r.get("local_path") if r else None
cover_wechat = r.get("wechat_url") if r else None
print(" 本地: %s" % (cover_local or "无"))
print(" 微信: %s..." % (cover_wechat[:40] if cover_wechat else "无"))

# 4. 上传播封面
thumb_id = None
if cover_local:
    thumb_id = upload_cover(cover_local)

# 5. 章节图
print("\n[4] 章节图...")
section_imgs = {}
for s in outline.get("sections", []):
    name = s.get("name", "")
    r = img_gen.generate_and_upload(name, [], material, "illustration")
    if r and r.get("wechat_url"):
        section_imgs[name] = r["wechat_url"]
        print("  %s: 成功" % name)

# 6. 写作
print("\n[5] 写作...")
article = writer.write_article(
    topic="OpenClaw 安装教程",
    outline=outline,
    generate_images=False,
    template={"type": "local", "id": "houge"},
    cover_image=cover_wechat,
    section_images=section_imgs
)
print(" 标题: %s" % article.get("title"))
print(" 模板: %s" % article.get("theme"))
print(" 字数: %d" % article.get("word_count", 0))

# 7. 发布
print("\n[6] 发布...")
draft_r = draft.create_draft([{
    "title": article.get("title"),
    "author": "贾维斯",
    "content": article.get("html"),
    "thumb_media_id": thumb_id,
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
    r = img_gen.generate_and_upload(topic, [], material, "cover")
    cover_l = r.get("local_path") if r else None
    cover_w = r.get("wechat_url") if r else None
    
    # 上传
    t_id = None
    if cover_l:
        t_id = upload_cover(cover_l)
    
    # 章节图
    secs = {}
    for s in outline.get("sections", []):
        r = img_gen.generate_and_upload(s.get("name", ""), [], material, "illustration")
        if r and r.get("wechat_url"):
            secs[s.get("name", "")] = r["wechat_url"]
    
    # 写作
    article = writer.write_article(
        topic=topic,
        outline=outline,
        generate_images=False,
        template={"type": "local", "id": tmpl},
        cover_image=cover_w,
        section_images=secs
    )
    
    # 发布
    dr = draft.create_draft([{
        "title": article.get("title"),
        "author": "贾维斯",
        "content": article.get("html"),
        "thumb_media_id": t_id,
        "content_source_url": "https://openclaw.ai"
    }])
    
    d_id = dr.get("media_id") if dr else None
    print("  -> 草稿: %s" % (d_id or "失败"))

print("\n" + "=" * 60)
print("完成")
print("=" * 60)
