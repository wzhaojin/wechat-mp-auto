"""
微信公众号自动化 - 文章写作 Skill
增加错误处理和安全性
"""

import re
import os
import uuid
import logging
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ArticleWriterSkill:
    """文章写作"""
    
    def __init__(self):
        self._themes_dir = Path(__file__).parent.parent.parent / "themes"
        self._image_generator = None
        self._cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"
    
    def _get_image_generator(self):
        """延迟加载图片生成器"""
        if self._image_generator is None:
            try:
                from .image_generator import ImageGeneratorSkill
                self._image_generator = ImageGeneratorSkill()
            except Exception as e:
                logger.warning(f"图片生成器初始化失败: {e}")
        return self._image_generator
    
    def write_article(self, topic: str, outline: Dict, template: Optional[Dict] = None, 
                      generate_images: bool = True) -> Dict:
        """撰写文章
        
        Args:
            topic: 文章主题
            outline: 文章大纲，包含 title 和 sections
            template: 模板配置
            generate_images: 是否自动生成配图（默认 True）
        """
        try:
            # 参数验证
            if not topic:
                raise ValueError("topic 不能为空")
            if not isinstance(outline, dict):
                raise ValueError("outline 必须是 dict")
            
            # 如果没有传 template，自动读取配置中的默认模板
            if template is None:
                from src.config import Config
                config = Config()
                template = config.get_default_template()
            
            theme = template.get("id", "default") if template else "default"
            
            # 生成内容
            sections = outline.get("sections", [])
            title = outline.get('title', topic)
            content_parts = [f"# {title}\n"]
            
            # 确保 cache 目录存在
            if not self._cache_dir.exists():
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. 生成封面图
            cover_path = None
            cover_filename = None
            
            if generate_images:
                img_gen = self._get_image_generator()
                if img_gen:
                    try:
                        logger.info(f"开始生成封面图: {title[:30]}...")
                        cover_path = img_gen.generate_cover(title, [])
                        if cover_path:
                            cover_filename = os.path.basename(cover_path)
                            logger.info(f"封面图已生成: {cover_filename}")
                    except Exception as e:
                        logger.warning(f"生成封面图失败: {e}")
            
            # 如果没有生成封面图，从 cache 中找一个
            if not cover_filename or not (self._cache_dir / cover_filename).exists():
                existing_covers = list(self._cache_dir.glob("cover_*.jpg"))
                if existing_covers:
                    cover_filename = existing_covers[0].name
                    logger.info(f"使用已有封面图: {cover_filename}")
                else:
                    cover_filename = f"cover_{uuid.uuid4().hex[:8]}.jpg"
            
            content_parts.insert(0, f"![封面]({cover_filename})\n\n")
            
            # 2. 生成章节内容（每章插入插图）
            for i, section in enumerate(sections):
                section_name = section.get("name", "")
                key_points = section.get("key_points", [])
                
                content_parts.append(f"## {section_name}\n")
                
                # 在每个章节开头插入插图
                illust_filename = None
                if generate_images and section_name:
                    img_gen = self._get_image_generator()
                    if img_gen:
                        try:
                            illust_path = img_gen.generate_illustration(section_name, [])
                            if illust_path:
                                illust_filename = os.path.basename(illust_path)
                                logger.info(f"章节插图已生成: {illust_filename}")
                        except Exception as e:
                            logger.warning(f"生成章节插图失败: {e}")
                
                # 如果没有生成插图，从 cache 中找一个
                if not illust_filename or not (self._cache_dir / illust_filename).exists():
                    existing_illusts = list(self._cache_dir.glob("illustration_*.jpg"))
                    if existing_illusts:
                        # 使用不同的插图（循环使用）
                        illust_filename = existing_illusts[i % len(existing_illusts)].name
                        logger.info(f"使用已有插图: {illust_filename}")
                    else:
                        illust_filename = f"illustration_{uuid.uuid4().hex[:8]}.jpg"
                
                # 章节插图始终插入
                if section_name:
                    content_parts.append(f"![{section_name}]({illust_filename})\n\n")
                
                for point in key_points:
                    content_parts.append(f"### {point}\n")
                    content_parts.append(f"这是关于 {point} 的详细内容...\n\n")
            
            markdown_content = "".join(content_parts)
            html_content = self.convert_to_html(markdown_content, theme)
            
            return {
                "topic": topic,
                "title": title,
                "markdown": markdown_content,
                "html": html_content,
                "word_count": self.count_words(markdown_content),
                "outline": outline,
                "theme": theme,
                "cover_path": cover_path,
                "images_generated": generate_images
            }
        except Exception as e:
            logger.error(f"write_article 错误: {e}")
            raise
    
    def count_words(self, content: str) -> int:
        """统计字数"""
        try:
            chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
            english = len(re.findall(r'[a-zA-Z]+', content))
            return chinese + english
        except Exception as e:
            logger.error(f"count_words 错误: {e}")
            return 0
    
    def convert_to_html(self, markdown: str, theme: str = "default") -> str:
        """Markdown 转微信 HTML"""
        try:
            import yaml
            
            theme_file = self._themes_dir / f"{theme}.yaml"
            if theme_file.exists():
                with open(theme_file) as f:
                    theme_config = yaml.safe_load(f) or {}
            else:
                theme_config = {"colors": {"primary": "#007AFF"}, "body": {"font_size": "15px", "color": "#333"}}
            
            primary = theme_config.get("colors", {}).get("primary", "#007AFF")
            
            html = ['<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: #333; line-height: 1.8;">']
            
            # 按行处理，保留代码块和引用块
            lines = markdown.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # 代码块 ```
                if line.strip().startswith('```'):
                    lang = line.strip()[3:].strip() if len(line.strip()) > 3 else ''
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        code_lines.append(lines[i])
                        i += 1
                    code_content = '\n'.join(code_lines)
                    # 转义 HTML
                    code_content = code_content.replace("<", "&lt;").replace(">", "&gt;")
                    html.append(f'<pre style="background:#f5f5f5;padding:12px;border-radius:8px;overflow-x:auto;font-family:monospace;font-size:13px;margin:12px 0;"><code>{code_content}</code></pre>')
                    i += 1
                    continue
                
                # 引用块 >
                if line.strip().startswith('>'):
                    quote_lines = [line.strip()[1:].strip()]
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith('>'):
                        quote_lines.append(lines[i].strip()[1:].strip())
                        i += 1
                    quote_content = '\n'.join(quote_lines)
                    quote_content = self._convert_inline_formatting(quote_content)
                    html.append(f'<blockquote style="border-left:4px solid {primary};padding-left:16px;margin:12px 0;color:#666;font-style:italic;">{quote_content}</blockquote>')
                    continue
                
                line = line.strip()
                if not line:
                    i += 1
                    continue
                
                # 标题
                if line.startswith('# '):
                    html.append(f'<h1 style="font-size: 24px; font-weight: bold; text-align: center; color: {primary}; margin: 20px 0;">{line[2:]}</h1>')
                elif line.startswith('## '):
                    html.append(f'<h2 style="font-size: 20px; font-weight: bold; margin: 16px 0;">{line[3:]}</h2>')
                elif line.startswith('### '):
                    html.append(f'<h3 style="font-size: 16px; font-weight: bold; margin: 12px 0;">{line[4:]}</h3>')
                # 无序列表
                elif line.startswith('- ') or line.startswith('* '):
                    content = line[2:]
                    content = self._convert_inline_formatting(content)
                    content = self._escape_user_html(content)
                    html.append(f'<p style="margin: 8px 0; padding-left: 20px;"><span style="margin-right:8px;">•</span>{content}</p>')
                # 有序列表
                elif line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                    match = re.match(r'^(\d+)\. (.+)$', line)
                    if match:
                        num, content = match.groups()
                        content = self._convert_inline_formatting(content)
                        content = self._escape_user_html(content)
                        html.append(f'<p style="margin: 8px 0; padding-left: 20px;"><span style="margin-right:8px;">{num}.</span>{content}</p>')
                    else:
                        # 普通段落
                        line = self._convert_inline_formatting(line)
                        line = self._escape_user_html(line)
                        html.append(f'<p style="margin: 8px 0;">{line}</p>')
                else:
                    # 普通段落
                    line = self._convert_inline_formatting(line)
                    # 保护已生成的 HTML 标签不被转义
                    line = self._escape_user_html(line)
                    html.append(f'<p style="margin: 8px 0;">{line}</p>')
                
                i += 1
            
            html.append('</div>')
            return '\n'.join(html)
        except Exception as e:
            logger.error(f"convert_to_html 错误: {e}")
            raise
    
    def _convert_inline_formatting(self, text: str) -> str:
        """转换行内格式：加粗、斜体、链接、图片"""
        # 图片 ![alt](url) -> 暂时返回原始格式，后续由 insert_images 处理
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
        
        # 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#007AFF;text-decoration:none;">\1</a>', text)
        
        # 加粗 **text** 或 __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
        
        # 斜体 *text* 或 _text_
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
        
        # 行内代码 `code`
        text = re.sub(r'`([^`]+)`', r'<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;">\1</code>', text)
        
        return text
    
    def _escape_user_html(self, text: str) -> str:
        """转义用户原始文本中的 HTML 标签，保护已生成的标签"""
        
        # 使用占位符保护已生成的 HTML 标签（先保护长的，再保护短的）
        protected = []
        def protect_tag(match):
            idx = len(protected)
            protected.append(match.group(0))
            return f"__HTML_PLACEHOLDER_{idx}__"
        
        # 保护完整标签（按长度从长到短）
        patterns = [
            r'<code[^>]*>[^<]*</code>',  # <code>...</code>
            r'<a[^>]*>[^<]*</a>',        # <a>...</a>
            r'<img[^>]*/?>',              # <img ... />
            r'<(/?)(strong|em|blockquote|pre|p|span|h[123])(\s|>)',  # 其他标签
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, protect_tag, text)
        
        # 转义用户原始文本中的 HTML
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        
        # 恢复已保护的标签
        for idx, tag in enumerate(protected):
            text = text.replace(f"__HTML_PLACEHOLDER_{idx}__", tag)
        
        return text
    
    def get_themes(self) -> List[str]:
        """获取主题列表"""
        try:
            themes = []
            if self._themes_dir.exists():
                for f in self._themes_dir.glob("*.yaml"):
                    themes.append(f.stem)
            return themes if themes else ["default"]
        except Exception as e:
            logger.error(f"get_themes 错误: {e}")
            return ["default"]
