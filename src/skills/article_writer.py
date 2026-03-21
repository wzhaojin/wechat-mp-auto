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
                from config import Config
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
            
            # 优先使用预设的章节图片URL（在 generate_images 条件之外）
            if section_images:
                for section_name, section_url in section_images.items():
                    section_wechat_urls[section_name] = section_url
                    logger.info(f"使用预设章节图: {section_name}")
            
            # 只有需要自动生成时才进入图片生成逻辑
            if generate_images and material_skill:
                img_gen = self._get_image_generator()
                if img_gen:
                    for i, section in enumerate(sections):
                        section_name = section.get("name", "")
                        if not section_name:
                            continue
                        
                        # 跳过已有预设图片的章节（已在上面处理）
                        if section_name in section_wechat_urls:
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
            # 如果传入了 content（AI生成的完整内容），优先使用
            if content and isinstance(content, str) and content.strip():
                logger.info(f"使用预设内容，字数: {len(content)}")
                markdown_content = content.strip()
                
                # 插入封面图（插到标题之后）
                if cover_wechat_url:
                    # 尝试找到第一个标题，把封面图插到它后面
                    title_match = re.search(r'^(#{1,6}\s+.+?\n)', markdown_content, re.MULTILINE)
                    if title_match:
                        pos = title_match.end()
                        markdown_content = markdown_content[:pos] + f"\n![封面]({cover_wechat_url})\n" + markdown_content[pos:]
                    else:
                        markdown_content = f"![封面]({cover_wechat_url})\n\n" + markdown_content
                
                # 插入章节图（在对应的 ## 标题后面）
                # AI 可能生成 "第X章: 引言" 格式的标题，需支持可选 "第X章:" 前缀
                CHAPTER_PREFIX = r'(?:第\d+[章节篇][：:\s]*)?'  # 可选的 "第X章:" 前缀
                for section_name, section_url in section_wechat_urls.items():
                    # 清理同一章节下可能残留的无效图片引用（本地路径或无效URL，非微信URL）
                    # 支持可选 "第X章:" 前缀
                    cleanup_pattern = r'^(\#{2,3}\s+' + CHAPTER_PREFIX + re.escape(section_name) + r'[^\n]*\n)\s*!\[([^\]]*)\]\((?!http)[^\)]+\)\n'
                    markdown_content = re.sub(cleanup_pattern, r'\1', markdown_content, flags=re.MULTILINE)

                    # 匹配 ## 章节名 或 ### 小节名，在标题行正后方插入图片（独占一行）
                    # 支持可选 "第X章:" 前缀
                    title_pattern = r'^(\#{2,3}\s+' + CHAPTER_PREFIX + re.escape(section_name) + r'[^\n]*\n)'
                    # 如果标题行后方已有一行有效的微信图片，则跳过（避免重复）
                    already_injected = re.search(
                        r'^(\#{2,3}\s+' + CHAPTER_PREFIX + re.escape(section_name) + r'[^\n]*\n)\s*!\[([^\]]*)\]\(http[^\)]+\)\n',
                        markdown_content, flags=re.MULTILINE
                    )
                    if already_injected:
                        logger.info(f"章节[{section_name}]已有有效图片，跳过注入")
                        continue
                    # 否则注入图片（独占一行）
                    injection = r'\1' + f'![{section_name}]({section_url})\n'
                    markdown_content = re.sub(title_pattern, injection, markdown_content, flags=re.MULTILINE)
            else:
                # 没有预设内容，从大纲构建
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
    
    def _is_table_row(self, line: str) -> bool:
        """判断是否是大纲中的表格行"""
        line = line.strip()
        if not line.startswith('|') or not line.endswith('|'):
            return False
        # 至少有两列
        parts = [p.strip() for p in line.split('|')]
        parts = [p for p in parts if p]  # 去掉空字符串
        return len(parts) >= 2

    def _convert_table_block(self, lines: List[str], start_idx: int, primary: str) -> tuple:
        """转换表格块，返回 (html_lines, end_idx)"""
        table_lines = []
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                break
            # 检查是否是表格行（|开头和结尾）
            if not (line.startswith('|') and line.endswith('|')):
                break
            table_lines.append(line)
            i += 1
        
        if len(table_lines) < 2:
            return None, start_idx
        
        # 解析表格
        def parse_row(row: str) -> List[str]:
            parts = [p.strip() for p in row.split('|')]
            return [p for p in parts if p]  # 过滤空字符串
        
        rows = [parse_row(line) for line in table_lines]
        
        # 检查是否有分隔行（第二行是 --- 等）
        has_header_separator = False
        if len(rows) >= 2:
            second_row = rows[1]
            if all(re.match(r'^[-:]+$', cell) for cell in second_row):
                has_header_separator = True
        
        # 构建HTML表格
        table_html = ['<table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">']
        
        # 表头
        header_cells = rows[0]
        table_html.append('  <thead><tr>')
        for cell in header_cells:
            cell_content = self._convert_inline_formatting(cell)
            cell_content = self._escape_user_html(cell_content)
            table_html.append(f'    <th style="border:1px solid #ddd;padding:8px 12px;background:#f5f5f5;font-weight:bold;text-align:left;">{cell_content}</th>')
        table_html.append('  </tr></thead>')
        
        # 表体
        body_start = 2 if has_header_separator else 1
        if body_start < len(rows):
            table_html.append('  <tbody>')
            for row in rows[body_start:]:
                table_html.append('    <tr>')
                for cell in row:
                    cell_content = self._convert_inline_formatting(cell)
                    cell_content = self._escape_user_html(cell_content)
                    table_html.append(f'      <td style="border:1px solid #ddd;padding:8px 12px;">{cell_content}</td>')
                table_html.append('    </tr>')
            table_html.append('  </tbody>')
        
        table_html.append('</table>')
        return table_html, i

    def _read_theme(self, theme: str) -> dict:
        """读取并解析 theme YAML，返回扁平化配置字典"""
        import yaml
        theme_file = self._themes_dir / f"{theme}.yaml"
        if theme_file.exists():
            with open(theme_file) as f:
                return yaml.safe_load(f) or {}
        return {}

    def _gv(self, d: dict, *keys, default: str = "") -> str:
        """安全获取嵌套字典值，避免 None"""
        v = d
        for k in keys:
            if isinstance(v, dict):
                v = v.get(k)
                if v is None:
                    return default
            else:
                return default
        return v if v else default

    def convert_to_html(self, markdown: str, theme: str = "default") -> str:
        """Markdown 转微信 HTML"""
        try:
            cfg = self._read_theme(theme)

            # 颜色
            primary = self._gv(cfg, "colors", "primary", default="#007AFF")
            text_c  = self._gv(cfg, "colors", "text", default="#333333")
            body_bg = self._gv(cfg, "colors", "background", default="")

            # body
            body_fs = self._gv(cfg, "body", "font_size", default="15px")
            body_lh = self._gv(cfg, "body", "line_height", default="1.8")

            # h1
            h1_fs    = self._gv(cfg, "h1", "font_size", default="22px")
            h1_align = self._gv(cfg, "h1", "text_align", default="center")
            h1_mgn   = self._gv(cfg, "h1", "margin", default="20px 0")
            h1_color = self._gv(cfg, "h1", "color", default=primary)

            # h2
            h2_fs    = self._gv(cfg, "h2", "font_size", default="18px")
            h2_mgn   = self._gv(cfg, "h2", "margin", default="20px 0 12px")
            h2_sec   = self._gv(cfg, "colors", "secondary", default=primary)
            h2_color = self._gv(cfg, "h2", "color", default=h2_sec)

            # h3
            h3_fs    = self._gv(cfg, "h3", "font_size", default="15px")
            h3_mgn   = self._gv(cfg, "h3", "margin", default="16px 0 10px")
            h3_color = self._gv(cfg, "h3", "color", default=text_c)

            # p
            p_mgn = self._gv(cfg, "p", "margin", default="14px 0")

            # link
            link_c  = self._gv(cfg, "link", "color", default=primary)
            link_dec = self._gv(cfg, "link", "text_decoration", default="none")

            # blockquote
            bq_color = self._gv(cfg, "blockquote", "color", default="#666666")
            bq_bg    = self._gv(cfg, "blockquote", "background_color", default="#fff8f0")
            bq_pad   = self._gv(cfg, "blockquote", "padding", default="10px 16px")
            bq_mgn   = self._gv(cfg, "blockquote", "margin", default="16px 0")

            # ul
            ul_mgn = self._gv(cfg, "ul", "margin", default="12px 0")
            ul_pl  = self._gv(cfg, "ul", "padding_left", default="20px")
            ul_bc  = self._gv(cfg, "ul", "bullet_color", default=primary)

            # ol
            ol_mgn = self._gv(cfg, "ol", "margin", default="12px 0")
            ol_pl  = self._gv(cfg, "ol", "padding_left", default="20px")
            ol_nc  = self._gv(cfg, "ol", "number_color", default=primary)

            # 外层容器：最大宽度 + 居中
            bg_style = f"background:{body_bg};" if body_bg else ""
            wrapper_style = (
                f"font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
                f"color:{text_c};line-height:{body_lh};font-size:{body_fs};"
                f"max-width:680px;margin:0 auto;padding:24px 20px;{bg_style}"
            )

            # 链接样式注入（覆盖行内 style）
            link_style = f'a {{color:{link_c};text-decoration:{link_dec};}}'
            html = [f'<div style="{wrapper_style}"><style>{link_style}</style>']

            lines = markdown.split('\n')
            i = 0
            pending_ul_lines = []
            pending_ol_lines = []

            def flush_ul():
                if not pending_ul_lines:
                    return
                html.append(
                    f'<ul style="margin:{ul_mgn};padding-left:0;list-style:none;">'
                )
                for ln in pending_ul_lines:
                    ln = self._convert_inline_formatting(ln)
                    ln = self._escape_user_html(ln)
                    html.append(
                        f'<li style="margin:6px 0;padding-left:16px;position:relative;color:{text_c};line-height:{body_lh};">'
                        f'<span style="position:absolute;left:0;top:0;color:{ul_bc};font-weight:bold;line-height:{body_lh};">•</span>'
                        f'{ln}</li>'
                    )
                html.append('</ul>')
                pending_ul_lines.clear()

            def flush_ol():
                if not pending_ol_lines:
                    return
                html.append(
                    f'<ol style="margin:{ol_mgn};padding-left:{ol_pl};list-style:none;counter-reset:ol-counter;">'
                )
                for ln in pending_ol_lines:
                    ln = self._convert_inline_formatting(ln)
                    ln = self._escape_user_html(ln)
                    html.append(
                        f'<li style="margin:6px 0;padding-left:12px;position:relative;color:{text_c};line-height:{body_lh};'
                        f'counter-increment:ol-counter;">'
                        f'<span style="position:absolute;left:0;color:{ol_nc};font-weight:bold;"></span>'
                        f'{ln}</li>'
                    )
                html.append('</ol>')
                pending_ol_lines.clear()

            while i < len(lines):
                raw_line = lines[i]
                line = raw_line.strip()

                # 空行：flush 列表
                if not line:
                    flush_ul()
                    flush_ol()
                    i += 1
                    continue

                # 分隔线 ---
                if line == '---':
                    flush_ul()
                    flush_ol()
                    html.append('<hr style="border:none;border-top:1px solid #e8e8e8;margin:24px 0;">')
                    i += 1
                    continue

                # 缩进代码块（4个以上空格开头，或 tab 开头）
                if raw_line.startswith('    ') or raw_line.startswith('\t'):
                    flush_ul()
                    flush_ol()
                    # 收集所有缩进行
                    code_lines = [line]
                    i += 1
                    while i < len(lines) and (lines[i].startswith('    ') or lines[i].startswith('\t') or lines[i].strip() == ''):
                        code_lines.append(lines[i].strip())
                        i += 1
                    code_content = '\n'.join(code_lines)
                    code_content = code_content.replace("<", "&lt;").replace(">", "&gt;")
                    html.append(
                        f'<pre style="background:#f5f5f5;padding:12px 16px;border-radius:8px;'
                        f'overflow-x:auto;font-family:monospace;font-size:13px;margin:16px 0;'
                        f'line-height:1.6;border:1px solid #e8e8e8;">'
                        f'<code>{code_content}</code></pre>'
                    )
                    continue

                # 代码块（``` 形式）
                if line.startswith('```'):
                    flush_ul()
                    flush_ol()
                    code_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        code_lines.append(lines[i])
                        i += 1
                    code_content = '\n'.join(code_lines)
                    code_content = code_content.replace("<", "&lt;").replace(">", "&gt;")
                    html.append(
                        f'<pre style="background:#f5f5f5;padding:12px 16px;border-radius:8px;'
                        f'overflow-x:auto;font-family:monospace;font-size:13px;margin:16px 0;'
                        f'line-height:1.6;border:1px solid #e8e8e8;">'
                        f'<code>{code_content}</code></pre>'
                    )
                    i += 1
                    continue

                # 引用块
                if line.startswith('>'):
                    flush_ul()
                    flush_ol()
                    quote_lines = [line[1:].strip()]
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith('>'):
                        quote_lines.append(lines[i].strip()[1:].strip())
                        i += 1
                    quote_content = '\n'.join(quote_lines)
                    quote_content = self._convert_inline_formatting(quote_content)
                    html.append(
                        f'<blockquote style="'
                        f'border-left:4px solid {primary};'
                        f'background:{bq_bg};'
                        f'padding:{bq_pad};'
                        f'margin:{bq_mgn};'
                        f'color:{bq_color};'
                        f'font-style:italic;'
                        f'border-radius:0 4px 4px 0;">'
                        f'{quote_content}</blockquote>'
                    )
                    continue

                # 表格块
                if self._is_table_row(line):
                    flush_ul()
                    flush_ol()
                    table_html, next_i = self._convert_table_block(lines, i, primary)
                    if table_html:
                        html.extend(table_html)
                        i = next_i
                    continue

                # 标题
                if line.startswith('# '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h1 style="font-size:{h1_fs};font-weight:bold;'
                        f'text-align:{h1_align};color:{h1_color};'
                        f'margin:{h1_mgn};line-height:1.4;">'
                        f'{self._escape_user_html(line[2:])}</h1>'
                    )
                elif line.startswith('## '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h2 style="font-size:{h2_fs};font-weight:bold;'
                        f'color:{h2_color};margin:{h2_mgn};line-height:1.4;'
                        f'border-left:4px solid {h2_sec};padding-left:10px;">'
                        f'{self._escape_user_html(line[3:])}</h2>'
                    )
                elif line.startswith('### '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h3 style="font-size:{h3_fs};font-weight:bold;'
                        f'color:{h3_color};margin:{h3_mgn};line-height:1.4;">'
                        f'{self._escape_user_html(line[4:])}</h3>'
                    )
                elif line.startswith('#### '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h4 style="font-size:15px;font-weight:bold;'
                        f'color:{h3_color};margin:{h3_mgn};line-height:1.4;">'
                        f'{self._escape_user_html(line[5:])}</h4>'
                    )
                elif line.startswith('##### '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h5 style="font-size:14px;font-weight:bold;'
                        f'color:{h3_color};margin:{h3_mgn};line-height:1.4;">'
                        f'{self._escape_user_html(line[6:])}</h5>'
                    )
                elif line.startswith('###### '):
                    flush_ul()
                    flush_ol()
                    html.append(
                        f'<h6 style="font-size:13px;font-weight:bold;'
                        f'color:{h3_color};margin:{h3_mgn};line-height:1.4;">'
                        f'{self._escape_user_html(line[7:])}</h6>'
                    )
                # 任务列表：- [ ] 或 - [x]（必须在普通列表之前检测）
                elif re.match(r'^(\s*)- \[([ xX])\] (.+)$', line):
                    flush_ul()
                    flush_ol()
                    indent = len(re.match(r'^(\s*)', line).group(1))
                    checked = re.match(r'^(\s*)- \[([ xX])\] (.+)$', line).group(2).lower() == 'x'
                    text = re.match(r'^(\s*)- \[([ xX])\] (.+)$', line).group(3)
                    text = self._convert_inline_formatting(text)
                    text = self._escape_user_html(text)
                    checkbox = 'checked' if checked else ''
                    checkbox_html = (
                        f'<input type="checkbox" disabled {checkbox} '
                        f'style="margin-right:8px;vertical-align:middle;pointer-events:none;">'
                    )
                    html.append(
                        f'<div style="margin:10px 0;display:flex;align-items:flex-start;">'
                        f'{checkbox_html}<span>{text}</span></div>'
                    )
                    i += 1
                    continue

                # 无序列表：暂存
                elif line.startswith('- ') or line.startswith('* '):
                    pending_ul_lines.append(line[2:])
                    pending_ol_lines.clear()
                # 有序列表：暂存
                elif re.match(r'^\d+\.\s', line):
                    flush_ul()
                    m = re.match(r'^\d+\.\s+(.*)$', line)
                    if m:
                        pending_ol_lines.append(m.group(1))
                # 普通段落
                else:
                    flush_ul()
                    flush_ol()
                    line = self._convert_inline_formatting(line)
                    line = self._escape_user_html(line)
                    # 图片行：检测是否为封面图（alt 含"封面"），封面图 full-width
                    img_match = re.match(r'^<img[^>]+alt="([^"]*)"[^>]*>$', line)
                    if img_match:
                        # 图片：保持 bare img，跟旧版完全一致，不加任何额外 inline style
                        html.append(f'<p style="margin:14px 0;text-align:center;">{line}</p>')
                    else:
                        # 没有 alt 匹配，当普通段落处理
                        html.append(
                            f'<p style="margin:{p_mgn};color:{text_c};line-height:{body_lh};">{line}</p>'
                        )

                i += 1

            flush_ul()
            flush_ol()
            html.append('</div>')
            return '\n'.join(html)
        except Exception as e:
            logger.error(f"convert_to_html 错误: {e}")
            raise
    
    def _convert_inline_formatting(self, text: str) -> str:
        """转换行内格式：加粗、斜体、链接、图片"""
        # 0. 保护 HTML 属性中的 URL 和属性值（先于所有转换）
        #    使用占位符保护 src/href 属性值中的 URL，避免下划线等被错误转换
        protected = []
        def protect_url(match):
            idx = len(protected)
            protected.append(match.group(0))
            return f"__PROTECTED_URL_{idx}__"
        
        # 保护 src= 和 href= 属性值（URL）
        text = re.sub(r'(src|href)="([^"]+)"', protect_url, text)
        
        # 1. 处理 markdown 图片 ![alt](url) -> <img src="url" alt="alt" />
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" />', text)
        
        # 2. 链接 [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#007AFF;text-decoration:none;">\1</a>', text)
        
        # 3. 加粗 **text** 或 __text__
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
        
        # 4. 斜体 *text* 或 _text_
        # 使用负向预见断言：确保符号两侧不是 URL 字符
        # *斜体* 处理
        text = re.sub(r'(?<![a-zA-Z0-9/:.?=&%-])\*([^*]+)\*(?![a-zA-Z0-9/:.?=&%-])', r'<em>\1</em>', text)
        text = re.sub(r'(?<![a-zA-Z0-9])\*([^*]+)\*(?![a-zA-Z0-9])', r'<em>\1</em>', text)
        # _斜体_ 处理
        text = re.sub(r'(?<![a-zA-Z0-9/:.?=&%-])_([^_]+)_(?![a-zA-Z0-9/:.?=&%-])', r'<em>\1</em>', text)
        text = re.sub(r'(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])', r'<em>\1</em>', text)
        
        # 5. 行内代码 `code`
        text = re.sub(r'`([^`]+)`', r'<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:13px;">\1</code>', text)

        # 6. 删除线 ~~text~~
        text = re.sub(r'~~([^~]+)~~', r'<del style="color:#999;text-decoration:line-through;">\1</del>', text)

        # 7. 上标 ^text^
        text = re.sub(r'\^([^^]+)\^', r'<sup style="font-size:0.8em;vertical-align:super;">\1</sup>', text)

        # 8. 下标 ~text~
        text = re.sub(r'~([^~]+)~', r'<sub style="font-size:0.8em;vertical-align:sub;">\1</sub>', text)

        # 9. 高亮 ==text== （仅匹配独立行内，非表格/代码内）
        text = re.sub(r'==([^=]+)==', r'<mark style="background:#FFF176;padding:1px 3px;border-radius:3px;">\1</mark>', text)

        # 10. 恢复被保护的 URL
        for idx, url in enumerate(protected):
            text = text.replace(f"__PROTECTED_URL_{idx}__", url)

        # 11. 保护生成的HTML标签（避免后续处理被转义）
        text = self._protect_html_tags(text)

        return text
    
    def _escape_user_html(self, text: str) -> str:
        """转义用户原始文本中的 HTML 标签，跳过已保护标签"""
        # 先用占位符保护已生成的HTML标签
        protected = []
        def ph(m):
            idx = len(protected)
            protected.append(m.group(0))
            return f"__HTAG_{idx}__"

        # 保护已生成的安全标签
        for t in ('div','span','p','h1','h2','h3','h4','h5','h6',
                  'ul','ol','li','blockquote','pre','code',
                  'table','thead','tbody','tr','th','td',
                  'a','strong','em','del','sup','sub','mark',
                  'details','summary','figure','figcaption',
                  'img','br','hr','input'):
            text = re.sub(f'<{t}[^>]*>.*?</{t}>', ph, text, flags=re.DOTALL)
            text = re.sub(f'<{t}[^>]*/?>', ph, text)

        # 转义剩余的用户原始HTML
        text = text.replace("<", "&lt;").replace(">", "&gt;")

        # 恢复被保护的标签
        for idx, tag in enumerate(protected):
            text = text.replace(f"__HTAG_{idx}__", tag)

        return text

    def _protect_html_tags(self, text: str) -> str:
        """保护已生成的 HTML 标签，用占位符替换，避免转义"""
        protected = []
        def ph(m):
            idx = len(protected)
            protected.append(m.group(0))
            return f"__HTAG_{idx}__"
        
        # 成对标签
        for t in ('div','span','p','h1','h2','h3','h4','h5','h6',
                  'ul','ol','li','blockquote','pre','code',
                  'table','thead','tbody','tr','th','td',
                  'a','strong','em','del','sup','sub','mark',
                  'details','summary','figure','figcaption'):
            text = re.sub(f'<{t}[^>]*>.*?</{t}>', ph, text, flags=re.DOTALL)
        
        # 自闭合标签
        for t in ('img','br','hr','input'):
            text = re.sub(f'<{t}[^>]*/?>', ph, text)
        
        # 恢复占位符
        for idx, tag in enumerate(protected):
            text = text.replace(f"__HTAG_{idx}__", tag)
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
            "houge": {
                "name_cn": "猴哥",
                "name_en": "houge",
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
