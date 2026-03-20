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
                      generate_images: bool = True,
                      material_skill=None,
                      content: Optional[str] = None,
                      section_images: Optional[Dict[str, str]] = None,
                      cover_image: Optional[str] = None) -> Dict:
        """撰写文章
        
        Args:
            topic: 文章主题
            outline: 文章大纲，包含 title 和 sections
            template: 模板配置
            generate_images: 是否自动生成配图（默认 True）
            material_skill: 素材管理技能实例，用于上传图片（可选）
            content: 预设的文章内容（markdown格式），有值时优先使用此内容而非outline生成
            section_images: 预设的章节图片URL字典，格式 {"章节名": "图片URL"}
            cover_image: 预设的封面图片URL，有值时跳过封面生成
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
            
            # 确保 cache 目录存在
            if not self._cache_dir.exists():
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 用于跟踪所有图片URL（local_path -> wechat_url）
            image_url_map = {}
            
            # ========== 1. 处理封面图 ==========
            cover_wechat_url = cover_image  # 预设的封面URL
            cover_path = None
            
            if not cover_wechat_url and generate_images:
                img_gen = self._get_image_generator()
                if img_gen and material_skill:
                    # 检查用户是否已完成图片来源选择
                    choice_check = img_gen._check_and_prompt_selection("cover")
                    if not choice_check.get("proceed"):
                        # 返回选择提示，终止生成流程
                        return {
                            "need_user_choice": True,
                            "choice_type": choice_check["choice_info"].get("choice_type"),
                            "choice_info": choice_check["choice_info"],
                        }
                    try:
                        logger.info(f"开始生成并上传封面图: {title[:30]}...")
                        kw = outline.get("cover_keywords", []) if isinstance(outline.get("cover_keywords"), list) else []
                        cover_result = img_gen.generate_and_upload(title, kw, material_skill, "cover")
                        if cover_result.get("wechat_url"):
                            cover_wechat_url = cover_result["wechat_url"]
                            cover_path = cover_result.get("local_path")
                            image_url_map[cover_path] = cover_wechat_url
                            logger.info(f"封面上传成功: {cover_wechat_url[:50]}...")
                    except Exception as e:
                        logger.warning(f"封面图生成上传失败: {e}")
            
            # ========== 2. 处理章节插图 ==========
            section_wechat_urls = {}  # {section_name: wechat_url}
            
            if generate_images and material_skill:
                img_gen = self._get_image_generator()
                if img_gen:
                    for i, section in enumerate(sections):
                        section_name = section.get("name", "")
                        if not section_name:
                            continue
                        
                        # 优先使用预设的图片URL
                        if section_images and section_name in section_images:
                            section_wechat_urls[section_name] = section_images[section_name]
                            logger.info(f"使用预设章节图: {section_name} -> {section_images[section_name][:50]}...")
                            continue
                        
                        # 自动生成并上传
                        try:
                            logger.info(f"生成章节{i+1}插图: {section_name}...")
                            kw = section.get("keywords", []) if isinstance(section.get("keywords"), list) else []
                            illust_result = img_gen.generate_and_upload(section_name, kw, material_skill, "illustration")
                            if illust_result.get("wechat_url"):
                                section_wechat_urls[section_name] = illust_result["wechat_url"]
                                image_url_map[illust_result.get("local_path", "")] = illust_result["wechat_url"]
                                logger.info(f"章节{i+1}上传成功: {illust_result['wechat_url'][:50]}...")
                        except Exception as e:
                            logger.warning(f"生成章节插图失败: {section_name} - {e}")
            
            # ========== 3. 构建文章内容 ==========
            content_parts = [f"# {title}\n"]
            
            # 封面图
            if cover_wechat_url:
                content_parts.insert(0, f"![封面]({cover_wechat_url})\n\n")
            elif cover_path:
                # 有本地路径但没上传成功，标记一下
                content_parts.insert(0, f"![封面]({cover_path})\n\n")
            
            # 章节内容
            for i, section in enumerate(sections):
                section_name = section.get("name", "")
                key_points = section.get("key_points", [])
                section_content = section.get("content", "")
                
                content_parts.append(f"\n## {section_name}\n")
                
                # 章节插图 - 优先用微信URL
                if section_name in section_wechat_urls:
                    content_parts.append(f"![{section_name}]({section_wechat_urls[section_name]})\n\n")
                
                # 如果有真实内容，使用它；否则用 key_points 生成
                if section_content:
                    content_parts.append(f"{section_content}\n")
                else:
                    for point in key_points:
                        content_parts.append(f"### {point}\n")
                        content_parts.append(f"这是关于 {point} 的详细内容...\n\n")
            
            markdown_content = "".join(content_parts)
            
            # ========== 4. 处理图片URL ==========
            # 将微信图片URL中的特殊字符（* _）编码，避免被markdown格式转换破坏
            # 例如: http://mmbiz.qpic.cn/sz*mmbiz*jpg -> http://mmbiz.qpic.cn/sz%2Ambiz%2Ajpg
            wx_url_map = {}  # 编码后URL -> 原始URL
            
            def encode_wx_url(match):
                alt_text = match.group(1)
                url = match.group(2)
                if url.startswith("http"):
                    # URL编码特殊字符，避免markdown处理破坏
                    safe_url = url.replace('*', '%2A').replace('_', '%5F')
                    wx_url_map[safe_url] = url  # 记录原始URL用于后续还原
                    return f"![{alt_text}]({safe_url})"
                # 本地路径：如果在 image_url_map 中有微信URL则替换
                if url in image_url_map:
                    safe_url = image_url_map[url].replace('*', '%2A').replace('_', '%5F')
                    wx_url_map[safe_url] = image_url_map[url]
                    return f"![{alt_text}]({safe_url})"
                logger.warning(f"图片未上传到微信: {url}")
                return match.group(0)
            
            markdown_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', encode_wx_url, markdown_content)
            
            # ========== 5. 转换为 HTML ==========
            html_content = self.convert_to_html(markdown_content, theme)
            
            # ========== 6. 还原微信图片URL ==========
            for safe_url, original_url in wx_url_map.items():
                html_content = html_content.replace(f'"{safe_url}"', f'"{original_url}"')
            
            return {
                "topic": topic,
                "title": title,
                "markdown": markdown_content,
                "html": html_content,
                "word_count": self.count_words(markdown_content),
                "outline": outline,
                "theme": theme,
                "cover_path": cover_path,
                "cover_wechat_url": cover_wechat_url,
                "section_images": section_wechat_urls,
                "images_generated": generate_images,
                "images_uploaded": len([v for v in image_url_map.values() if v.startswith("http")])
            }
        except Exception as e:
            logger.error(f"write_article 错误: {e}")
            raise
    
    def ensure_images_uploaded(self, content: str, material_skill) -> str:
        """
        安全网：确保内容中的所有图片都已上传到微信
        
        扫描 markdown 或 HTML 内容中的本地图片路径，
        自动上传到微信素材库并替换为微信URL。
        
        Args:
            content: markdown 或 HTML 内容
            material_skill: 素材管理技能实例
        
        Returns:
            替换后的内容，所有图片均使用微信URL
        """
        if not content or not material_skill:
            return content
        
        # 匹配本地图片路径（相对于cache目录的路径或绝对路径）
        import re
        from pathlib import Path
        
        cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"
        
        def replace_local_image(match):
            alt_or_tag = match.group(1) if match.lastindex >= 1 else ""
            path_or_url = match.group(2) if match.lastindex >= 2 else ""
            
            # 如果已经是http URL，跳过
            if path_or_url.startswith("http"):
                return match.group(0)
            
            # 跳过已经是完整URL的情况（markdown和HTML通用）
            if path_or_url.startswith("http"):
                return match.group(0)
            
            # 检查是否是本地文件
            local_path = Path(path_or_url)
            if not local_path.is_absolute():
                # 相对路径，尝试相对于cache目录
                local_path = cache_dir / path_or_url
            
            if not local_path.exists():
                logger.warning(f"本地图片不存在，跳过: {local_path}")
                return match.group(0)
            
            # 上传到微信
            try:
                logger.info(f"上传本地图片: {local_path}")
                result = material_skill.upload_image(str(local_path))
                wechat_url = result.get("url", "")
                media_id = result.get("media_id", "")
                
                if wechat_url:
                    logger.info(f"本地上传成功: {wechat_url[:50]}...")
                    # 替换URL
                    if match.lastindex and match.group(1):
                        # markdown格式 ![alt](path)
                        return f"![{alt_or_tag}]({wechat_url})"
                    else:
                        # 其他格式，替换path
                        return wechat_url
                else:
                    logger.warning(f"本地上传失败: {local_path}")
                    return match.group(0)
            except Exception as e:
                logger.error(f"本地上传异常: {e}")
                return match.group(0)
        
        # 匹配 markdown 图片 ![alt](path)
        content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_local_image, content)
        
        # 匹配 HTML img 标签 src 属性中的本地路径
        content = re.sub(r'<img([^>]*)src="([^"]+)"([^>]*)>', 
                        lambda m: self._replace_html_img_src(m, material_skill), 
                        content)
        
        return content
    
    def _replace_html_img_src(self, match, material_skill):
        """替换HTML中img标签的本地src为微信URL"""
        before_src = match.group(1)
        src = match.group(2)
        after_src = match.group(3)
        
        if src.startswith("http"):
            return match.group(0)
        
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"
        
        local_path = Path(src)
        if not local_path.is_absolute():
            local_path = cache_dir / src
        
        if not local_path.exists():
            return match.group(0)
        
        try:
            result = material_skill.upload_image(str(local_path))
            wechat_url = result.get("url", "")
            if wechat_url:
                logger.info(f"HTML图片上传成功: {wechat_url[:50]}...")
                return f'<img{before_src}src="{wechat_url}"{after_src}>'
        except Exception as e:
            logger.warning(f"HTML图片上传失败: {e}")
        
        return match.group(0)

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
        # 1. 处理 markdown 图片 ![alt](url) -> <img src="url" alt="alt" />
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
        
        # 2. 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#007AFF;text-decoration:none;">\1</a>', text)
        
        # 3. 加粗 **text** 或 __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
        
        # 4. 斜体 *text* 或 _text_
        # 排除 HTML 属性上下文（如 src="url_with*text*"）
        # 简单判断：包含 = 的内容说明在 HTML 属性值中，跳过
        def convert_emphasis(match):
            inner = match.group(1)
            if '=' in inner:
                return match.group(0)
            return f'<em>{inner}</em>'
        
        text = re.sub(r'\*([^*]+)\*', convert_emphasis, text)
        text = re.sub(r'_([^_]+)_', convert_emphasis, text)
        
        # 5. 行内代码 `code`
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

    def preview_theme(self, theme_name: str = None) -> str:
        """
        生成模板预览 HTML。

        Args:
            theme_name: 指定模板名，为 None 时返回所有模板合并预览。

        Returns:
            HTML 字符串，可用 canvas.present(url="data:text/html,...") 渲染。
        """
        import yaml

        # 模板配色和底色配置
        theme_styles = {
            "default": {
                "name_cn": "默认",
                "name_en": "default",
                "primary": "#007AFF",
                "bg": "#f0f4ff",
                "label_bg": "#007AFF",
            },
            "henge": {
                "name_cn": "横戈",
                "name_en": "henge",
                "primary": "#333333",
                "bg": "#f0f0f0",
                "label_bg": "#333333",
            },
            "shuimo": {
                "name_cn": "水墨",
                "name_en": "shuimo",
                "primary": "#2c3e50",
                "bg": "#f5f5f0",
                "label_bg": "#2c3e50",
            },
            "wenyan": {
                "name_cn": "古文",
                "name_en": "wenyan",
                "primary": "#8b4513",
                "bg": "#fff8f0",
                "label_bg": "#8b4513",
            },
            "macaron": {
                "name_cn": "马卡龙",
                "name_en": "macaron",
                "primary": "#e91e8c",
                "bg": "#fef0f5",
                "label_bg": "#e91e8c",
            },
        }

        # 确定要预览哪些模板
        if theme_name:
            targets = {theme_name: theme_styles.get(theme_name, theme_styles["default"])}
        else:
            targets = theme_styles

        blocks = []
        for tid, style in targets.items():
            theme_file = self._themes_dir / f"{tid}.yaml"
            if theme_file.exists():
                with open(theme_file) as f:
                    cfg = yaml.safe_load(f) or {}
                primary = cfg.get("colors", {}).get("primary", style["primary"])
                bg = style["bg"]
            else:
                primary = style["primary"]
                bg = style["bg"]

            block = f'''
  <div style="background:{bg}; padding:24px; margin-bottom:20px; border-radius:4px;">
    <div style="display:inline-block; background:{style["label_bg"]}; color:#fff; padding:5px 12px; font-size:12px; border-radius:3px; margin-bottom:10px;">
      {style["name_cn"]} {style["name_en"]}
    </div>
    <h1 style="font-size:20px; color:{primary}; margin:8px 0;">示例标题</h1>
    <p style="color:#333; line-height:1.8; margin:8px 0;">正文示例文字，演示模板效果...</p>
    <blockquote style="border-left:3px solid {primary}; padding-left:10px; color:#666; margin:8px 0;">引用块效果</blockquote>
    <p style="margin:8px 0;"><strong>加粗</strong> · <em>斜体</em></p>
  </div>'''
            blocks.append(block)

        html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ margin:0; padding:24px; background:#fff; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
</style>
</head>
<body>
<div style="max-width:900px; margin:0 auto;">
  <h2 style="text-align:center; padding:16px 0; margin-bottom:24px; font-size:18px; color:#333;">
    微信公众号模板预览
  </h2>
  {"".join(blocks)}
</div>
</body>
</html>'''
        return html
