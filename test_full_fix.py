#!/usr/bin/env python3
"""
完整流程测试 - 修复版
使用真实的 AI 内容生成并推送到草稿箱
"""
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
print("完整流程测试（修复版）")
print("=" * 60)

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
token_mgr = TokenManager(app_id, app_secret)
material = MaterialSkill(token_mgr)
writer = ArticleWriterSkill()
draft = DraftSkill(token_mgr)
reviewer = ContentReviewerSkill()

# 1. 选题调研
print("\n[1] 选题调研...")
research = TopicResearchSkill()
res = research.research_topic("OpenClaw 安装教程")
print(f"  搜索结果: {len(res.get('search_results', []))} 条")

# 2. 生成大纲
print("\n[2] 生成大纲...")
outline = research.generate_outline("OpenClaw 安装教程", res)
print(f"  标题: {outline.get('title')}")
print(f"  章节数: {len(outline.get('sections', []))}")

# 3. 生成 AI 内容
print("\n[3] 生成 AI 内容...")
ai_content = research.generate_full_content(
    topic="OpenClaw 安装教程",
    outline=outline,
    research_data=res
)
print(f"  AI内容长度: {len(ai_content)} 字符")

# 4. 生成配图
print("\n[4] 生成配图...")
img_gen = ImageGeneratorSkill()
cover_result = img_gen.generate_and_upload("OpenClaw 安装教程", [], material, "cover")
cover_path = cover_result.get("local_path")
cover_url = cover_result.get("wechat_url")
print(f"  封面: {'成功 ' + cover_url[:40] + '...' if cover_url else '失败'}")
print(f"  本地路径: {cover_path}")

section_imgs = {}
for s in outline.get("sections", []):
    name = s.get("name", "")
    r = img_gen.generate_and_upload(name, [], material, "illustration")
    url = r.get("wechat_url")
    if url:
        section_imgs[name] = url
        print(f"  章节图-{name}: 成功")
    else:
        print(f"  章节图-{name}: 失败")

# 5. 生成文章（关键：传递 ai_content）
print("\n[5] 生成文章（传递 ai_content）...")
article = writer.write_article(
    topic="OpenClaw 安装教程",
    outline=outline,
    generate_images=False,
    template={"type": "local", "id": "houge"},
    cover_image=cover_url,
    section_images=section_imgs,
    content=ai_content  # 关键修复：传递 AI 内容
)

print(f"\n  标题: {article.get('title')}")
print(f"  字数: {article.get('word_count')}")
print(f"  markdown长度: {len(article.get('markdown', ''))}")
print(f"  html长度: {len(article.get('html', ''))}")

# 6. 审核
print("\n[6] 内容审核...")
review = reviewer.review_article({
    "markdown": article.get("markdown", ""),
    "content": article.get("html", "")
})
print(f"  审核通过: {review.get('passed')}")
print(f"  重复度: {review.get('plagiarism', {}).get('similarity', 0)}%")

# 7. 推送到草稿箱
print("\n[7] 推送到草稿箱...")
# 缩略图需要本地的 cover_path，不接受 URL
thumb_id = None
if cover_path and Path(cover_path).exists():
    try:
        thumb_r = material.upload_thumb(cover_path)
        thumb_id = thumb_r.get("media_id")
        print(f"  缩略图: {'成功 ' + str(thumb_id)[:20]}")
    except Exception as e:
        print(f"  缩略图失败: {e}")
else:
    print(f"  缩略图跳过（无本地路径或文件不存在）")

draft_r = draft.create_draft([{
    "title": article.get("title"),
    "author": "贾维斯",
    "content": article.get("html"),
    "thumb_media_id": thumb_id,
    "content_source_url": "https://openclaw.ai"
}])
if draft_r:
    print(f"  草稿: 成功，media_id={draft_r.get('media_id')}")
else:
    print(f"  草稿: 失败")

# 8. 打印 markdown 内容片段（用于排查）
print("\n[8] === Markdown 内容片段（前 2000 字符）===")
print(article.get("markdown", "")[:2000])

# 9. 打印 HTML 片段
print("\n[9] === HTML 内容片段（前 2000 字符）===")
print(article.get("html", "")[:2000])

print("\n完成！")
