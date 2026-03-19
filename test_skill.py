"""
微信公众号自动化 Skill - 正式测试
"""

import pytest
import sys
import os
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))


class TestConfig:
    """配置测试"""
    
    def test_config_import(self):
        """测试配置导入"""
        from config import Config
        assert Config is not None
    
    def test_config_get_credentials(self):
        """测试获取凭证"""
        from config import Config
        config = Config()
        app_id, app_secret = config.get_credentials()
        assert app_id is not None
        assert app_secret is not None


class TestTokenManager:
    """Token管理器测试"""
    
    def test_token_manager_import(self):
        """测试导入"""
        from token_manager import TokenManager
        assert TokenManager is not None
    
    def test_token_manager_init(self):
        """测试初始化"""
        from config import Config
        from token_manager import TokenManager
        config = Config()
        app_id, app_secret = config.get_credentials()
        token_mgr = TokenManager(app_id, app_secret)
        assert token_mgr is not None


class TestArticleWriterSkill:
    """文章写作测试"""
    
    def test_import(self):
        """测试导入"""
        from skills.article_writer import ArticleWriterSkill
        assert ArticleWriterSkill is not None
    
    def test_init(self):
        """测试实例化"""
        from skills.article_writer import ArticleWriterSkill
        writer = ArticleWriterSkill()
        assert writer is not None
    
    def test_get_themes(self):
        """测试获取主题列表"""
        from skills.article_writer import ArticleWriterSkill
        writer = ArticleWriterSkill()
        themes = writer.get_themes()
        assert len(themes) > 0
        assert "macaron" in themes
    
    def test_convert_to_html(self):
        """测试Markdown转HTML"""
        from skills.article_writer import ArticleWriterSkill
        writer = ArticleWriterSkill()
        
        md = "# 测试标题\n\n这是测试内容"
        html = writer.convert_to_html(md, "default")
        
        assert html is not None
        assert len(html) > 0
    
    def test_write_article(self):
        """测试生成文章"""
        from skills.article_writer import ArticleWriterSkill
        writer = ArticleWriterSkill()
        
        outline = {
            "title": "测试文章",
            "sections": [
                {"name": "第一章", "key_points": ["要点1"]}
            ]
        }
        
        result = writer.write_article("测试", outline, generate_images=False)
        
        assert "markdown" in result
        assert "html" in result
        assert result["title"] == "测试文章"


class TestContentReviewerSkill:
    """内容审核测试"""
    
    def test_import(self):
        """测试导入"""
        from skills.content_reviewer import ContentReviewerSkill
        assert ContentReviewerSkill is not None
    
    def test_init(self):
        """测试实例化"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        assert reviewer is not None
    
    def test_prohibited_words(self):
        """测试敏感词列表"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        
        assert "谣言" in reviewer.PROHIBITED_WORDS
        assert "诈骗" in reviewer.PROHIBITED_WORDS
    
    def test_review_normal_content(self):
        """测试正常内容审核"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        
        article = {"markdown": "这是一篇正常文章内容"}
        result = reviewer.review_article(article)
        
        assert result["passed"] == True
    
    def test_review_prohibited_content(self):
        """测试敏感词检测"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        
        article = {"markdown": "这篇文章包含谣言内容"}
        result = reviewer.review_article(article)
        
        assert result["passed"] == False
        assert len(result["prohibited"]["violations"]) > 0
    
    def test_plagiarism_check(self):
        """测试重复度检测"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        
        # 使用足够长的内容
        content1 = "这是一段很长的测试内容用于检测重复度，" * 10
        result1 = reviewer.check_plagiarism(content1)
        
        # 相似内容
        content2 = "这是一段很长的测试内容用于检测重复度，" * 10 + "额外内容"
        result2 = reviewer.check_plagiarism(content2)
        
        # 检查返回值包含 similarity 字段
        assert "similarity" in result2
    
    def test_clear_history(self):
        """测试清除历史"""
        from skills.content_reviewer import ContentReviewerSkill
        reviewer = ContentReviewerSkill()
        
        result = reviewer.clear_history()
        assert result["success"] == True


class TestUserSkill:
    """用户管理测试"""
    
    def test_import(self):
        """测试导入"""
        from skills.user_skill import UserSkill
        assert UserSkill is not None
    
    def test_init(self):
        """测试实例化"""
        from config import Config
        from token_manager import TokenManager
        from skills.user_skill import UserSkill
        
        config = Config()
        app_id, app_secret = config.get_credentials()
        token_mgr = TokenManager(app_id, app_secret)
        user_skill = UserSkill(token_mgr)
        
        assert user_skill is not None
    
    def test_load_user_cache(self):
        """测试加载用户缓存"""
        from skills.user_skill import UserSkill
        from config import Config
        from token_manager import TokenManager
        
        config = Config()
        app_id, app_secret = config.get_credentials()
        token_mgr = TokenManager(app_id, app_secret)
        user_skill = UserSkill(token_mgr)
        
        cache = user_skill._load_user_cache()
        assert "users" in cache
        assert "tags" in cache


class TestMessageSkill:
    """消息发送测试"""
    
    def test_import(self):
        """测试导入"""
        from skills.message_skill import MessageSkill
        assert MessageSkill is not None
    
    def test_init(self):
        """测试实例化"""
        from config import Config
        from token_manager import TokenManager
        from skills.message_skill import MessageSkill
        
        config = Config()
        app_id, app_secret = config.get_credentials()
        token_mgr = TokenManager(app_id, app_secret)
        msg_skill = MessageSkill(token_mgr)
        
        assert msg_skill is not None


class TestPublish:
    """发布功能测试"""
    
    def test_check_article_integrity_import(self):
        """测试导入"""
        from publish import check_article_integrity
        assert check_article_integrity is not None
    
    def test_check_markdown(self):
        """测试Markdown检查"""
        from publish import check_article_integrity
        
        md = "# 标题\n\n正文"
        result = check_article_integrity(markdown=md, stage="test")
        
        assert "passed" in result
        assert "stats" in result
    
    def test_check_html(self):
        """测试HTML检查"""
        from publish import check_article_integrity
        
        md = "# 标题"
        html = "<div><h1>标题</h1></div>"
        
        result = check_article_integrity(markdown=md, html=html, stage="test")
        
        assert "passed" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
