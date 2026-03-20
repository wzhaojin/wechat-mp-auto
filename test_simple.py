#!/usr/bin/env python3
"""简化版全流程测试 - 不带图片"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skills.topic_research import TopicResearchSkill
from skills.article_writer import ArticleWriterSkill
from skills.draft_skill import DraftSkill
from skills.content_reviewer import ContentReviewerSkill
from token_manager import TokenManager
from config import Config

print("=" * 60)
print("简化版全流程测试（无图片）")
print("=" * 60)

# 初始化
config = Config()
app_id, app_secret = config.get_credentials()
print("AppID: %s..." % app_id[:10])

token_mgr = TokenManager(app_id, app_secret)
draft = DraftSkill(token_mgr)
research = TopicResearchSkill()
writer = ArticleWriterSkill()
reviewer = ContentReviewerSkill()

# 测试1: 单篇（侯哥）
print("\n" + "=" * 50)
print("测试1: OpenClaw安装教程（侯哥模板）")
print("=" * 50)

# 调研
print("\n[1] 调研...")
result = research.research_topic("OpenClaw 安装教程")
print(" 搜索: %d条" % len(result.get("search_results", [])))

# 大纲
print("\n[2] 大纲...")
outline = research.generate_outline("OpenClaw 安装教程", result)
print(" 章节: %d个" % len(outline.get("sections", [])))

# 写作（无图片）
print("\n[3] 写作...")
article = writer.write_article(
    topic="OpenClaw 安装教程",
    outline=outline,
    generate_images=False,
    template={"type": "local", "id": "houge"}
)
print(" 标题: %s" % article.get("title"))
print(" 模板: %s" % article.get("theme"))
print(" 字数: %d" % article.get("word_count", 0))

# 审核
print("\n[4] 审核...")
rev = reviewer.review_article({
    "markdown": article.get("markdown", ""),
    "content": article.get("html", "")
})
print(" 结果: %s" % ("通过" if rev.get("passed") else "失败"))

# 发布（不带thumb_media_id，让系统自动处理）
print("\n[5] 发布...")
try:
    draft_r = draft.create_draft([{
        "title": article.get("title"),
        "author": "贾维斯",
        "content": article.get("html"),
        "content_source_url": "https://openclaw.ai"
    }])
    draft_id = draft_r.get("media_id") if draft_r else None
    print(" 草稿ID: %s" % (draft_id or "失败"))
except Exception as e:
    print(" 失败: %s" % e)
    draft_id = None

print("\n[结果] 标题=%s | 草稿=%s" % (article.get("title"), draft_id or "N/A"))


# 测试2: 批量3篇
print("\n" + "=" * 50)
print("测试2: 批量3篇（不同模板）")
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
    
    # 写作
    article = writer.write_article(
        topic=topic, 
        outline=outline,
        generate_images=False,
        template={"type": "local", "id": tmpl}
    )
    
    # 发布
    try:
        draft_r = draft.create_draft([{
            "title": article.get("title"),
            "author": "贾维斯",
            "content": article.get("html"),
            "content_source_url": "https://openclaw.ai"
        }])
        draft_id = draft_r.get("media_id") if draft_r else None
    except Exception as e:
        print(" 错误: %s" % e)
        draft_id = None
    
    print("  -> 草稿: %s" % (draft_id or "失败"))

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
