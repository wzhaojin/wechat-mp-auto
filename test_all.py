#!/usr/bin/env python3
"""
wechat-mp-auto 全面测试脚本
"""

import sys
import os
sys.path.insert(0, '/Users/wzj/.openclaw/workspace/skills/wechat-mp-auto/src')

from pathlib import Path
import tempfile

# 测试标记
TESTS_PASSED = 0
TESTS_FAILED = 0


def test(name, func):
    """运行单个测试"""
    global TESTS_PASSED, TESTS_FAILED
    try:
        result = func()
        if result:
            print(f"  ✓ {name}")
            TESTS_PASSED += 1
        else:
            print(f"  ✗ {name}")
            TESTS_FAILED += 1
    except Exception as e:
        print(f"  ✗ {name}: {e}")
        TESTS_FAILED += 1


def test_article_writer():
    """测试文章写作模块"""
    print("\n=== 测试: ArticleWriterSkill ===")
    from skills.article_writer import ArticleWriterSkill
    
    writer = ArticleWriterSkill()
    
    # 测试 Markdown 转换
    def test_basic_conversion():
        html = writer.convert_to_html("**加粗** 和 *斜体*", "default")
        return "<strong>" in html and "<em>" in html
    test("基本转换 (加粗/斜体)", test_basic_conversion)
    
    # 测试代码块
    def test_code_block():
        md = '''```
代码块内容
```'''
        html = writer.convert_to_html(md, "default")
        return "<pre" in html and "<code>" in html
    test("代码块转换", test_code_block)
    
    # 测试引用
    def test_quote():
        md = '''> 这是一段引用
> 多行引用'''
        html = writer.convert_to_html(md, "default")
        return "<blockquote" in html
    test("引用转换", test_quote)
    
    # 测试列表
    def test_list():
        html = writer.convert_to_html("- 项目1\n- 项目2", "default")
        return "•" in html or "li>" in html.lower()
    test("列表转换", test_list)
    
    # 测试链接
    def test_link():
        html = writer.convert_to_html("[链接](https://example.com)", "default")
        return "<a href=" in html
    test("链接转换", test_link)
    
    # 测试图片
    def test_image():
        html = writer.convert_to_html("![图片](test.jpg)", "default")
        return '<img src="test.jpg"' in html
    test("图片转换", test_image)
    
    # 测试主题
    def test_themes():
        themes = writer.get_themes()
        return isinstance(themes, list) and len(themes) > 0
    test("主题列表", test_themes)
    
    # 测试字数统计
    def test_word_count():
        count = writer.count_words("你好 world")
        return count >= 2
    test("字数统计", test_word_count)


def test_image_processor():
    """测试图片处理模块"""
    print("\n=== 测试: ImageProcessorSkill ===")
    from skills.image_processor import ImageProcessorSkill
    
    processor = ImageProcessorSkill()
    
    # 测试尺寸获取
    def test_get_size():
        size = processor._get_image_size(__file__)
        return isinstance(size, tuple) and len(size) == 2
    test("获取图片尺寸", test_get_size)
    
    # 测试格式转换
    def test_format():
        result = processor._convert_format(__file__, "jpg")
        return isinstance(result, str)
    test("格式转换函数", test_format)
    
    # 测试去水印函数存在
    def test_watermark_removal():
        return hasattr(processor, 'remove_watermark') and callable(processor.remove_watermark)
    test("去水印功能", test_watermark_removal)


def test_image_generator():
    """测试图片生成模块"""
    print("\n=== 测试: ImageGeneratorSkill ===")
    from skills.image_generator import ImageGeneratorSkill
    
    generator = ImageGeneratorSkill()
    
    # 测试初始化
    def test_init():
        return hasattr(generator, '_cache_dir')
    test("初始化", test_init)
    
    # 测试封面生成函数
    def test_cover_gen():
        return hasattr(generator, 'generate_cover')
    test("封面生成函数", test_cover_gen)
    
    # 测试插图生成函数
    def test_illust_gen():
        return hasattr(generator, 'generate_illustration')
    test("插图生成函数", test_illust_gen)
    
    # 测试文本配图
    def test_text_illust():
        return hasattr(generator, 'generate_by_text')
    test("文本配图函数", test_text_illust)


def test_topic_research():
    """测试选题调研模块"""
    print("\n=== 测试: TopicResearchSkill ===")
    from skills.topic_research import TopicResearchSkill
    
    research = TopicResearchSkill()
    
    # 测试函数存在
    def test_research():
        return hasattr(research, 'research_topic')
    test("调研函数存在", test_research)
    
    def test_outline():
        return hasattr(research, 'generate_outline')
    test("大纲生成函数存在", test_outline)
    
    # 测试大纲生成
    def test_generate_outline():
        result = research.generate_outline("测试主题", {})
        return isinstance(result, dict) and "sections" in result
    test("大纲生成", test_generate_outline)


def test_config():
    """测试配置模块"""
    print("\n=== 测试: Config ===")
    from config import Config
    
    config = Config()
    
    # 测试凭证获取
    def test_credentials():
        try:
            app_id, app_secret = config.get_credentials()
            return app_id is not None and app_secret is not None
        except:
            return False
    test("获取凭证", test_credentials)
    
    # 测试默认模板
    def test_template():
        template = config.get_default_template()
        return isinstance(template, dict)
    test("默认模板", test_template)


def test_token_manager():
    """测试 Token 管理"""
    print("\n=== 测试: TokenManager ===")
    from token_manager import TokenManager
    from config import Config
    
    config = Config()
    try:
        app_id, app_secret = config.get_credentials()
        
        # 测试初始化
        def test_init():
            mgr = TokenManager(app_id, app_secret)
            return hasattr(mgr, 'app_id')
        test("初始化", test_init)
        
        # 测试 Token 获取
        def test_token():
            mgr = TokenManager(app_id, app_secret)
            token = mgr.get_access_token()
            return isinstance(token, str) and len(token) > 0
        test("获取 Token", test_token)
        
    except Exception as e:
        print(f"  ⚠️ 跳过 Token 测试: {e}")


def test_material_skill():
    """测试素材管理"""
    print("\n=== 测试: MaterialSkill ===")
    from skills.material_skill import MaterialSkill
    from token_manager import TokenManager
    from config import Config
    
    try:
        config = Config()
        app_id, app_secret = config.get_credentials()
        mgr = TokenManager(app_id, app_secret)
        material = MaterialSkill(mgr)
        
        def test_init():
            return hasattr(material, 'upload_image')
        test("初始化", test_init)
        
    except Exception as e:
        print(f"  ⚠️ 跳过素材测试: {e}")


def test_publish_skill():
    """测试发布管理"""
    print("\n=== 测试: PublishSkill ===")
    from skills.publish_skill import PublishSkill
    
    # 测试类存在和函数
    def test_class():
        return hasattr(PublishSkill, 'publish_draft')
    test("发布函数存在", test_class)
    
    def test_list():
        return hasattr(PublishSkill, 'list_published')
    test("列表函数存在", test_list)
    
    def test_batch():
        return hasattr(PublishSkill, 'batch_publish')
    test("批量发布函数存在", test_batch)


def test_exceptions():
    """测试异常模块"""
    print("\n=== 测试: Exceptions ===")
    from exceptions import APIError, get_error_message
    
    # 测试 APIError
    def test_api_error():
        err = APIError(40001, "test error")
        return err.errcode == 40001
    test("APIError 异常", test_api_error)
    
    # 测试错误码映射
    def test_error_codes():
        msg = get_error_message(40001)
        return isinstance(msg, str)
    test("错误码映射", test_error_codes)


def test_publish_script():
    """测试发布脚本"""
    print("\n=== 测试: Publish Script ===")
    
    # 测试参数解析
    def test_args():
        import argparse
        sys.argv = ['publish.py', '--help']
        try:
            from publish import parse_args
            args = parse_args()
            return True
        except SystemExit:
            return True
        except:
            return False
    test("参数解析", test_args)
    
    # 测试日志配置
    def test_logging():
        from publish import setup_logging
        logger = setup_logging()
        return logger is not None
    test("日志配置", test_logging)


def main():
    global TESTS_PASSED, TESTS_FAILED
    
    print("=" * 60)
    print("wechat-mp-auto 全面测试")
    print("=" * 60)
    
    # 运行所有测试
    test_article_writer()
    test_image_processor()
    test_image_generator()
    test_topic_research()
    test_config()
    test_token_manager()
    test_material_skill()
    test_publish_skill()
    test_exceptions()
    test_publish_script()
    
    # 总结
    print("\n" + "=" * 60)
    print(f"测试结果: {TESTS_PASSED} 通过, {TESTS_FAILED} 失败")
    print("=" * 60)
    
    return TESTS_FAILED == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
