#!/usr/bin/env python3
"""
微信公众号文章发布脚本 - 优化版

用法:
    python3 publish.py --markdown <md文件> --title <标题> [选项]

选项:
    -m, --markdown          Markdown 文件路径
    -t, --title             文章标题
    -a, --author            作者 (默认: 贾维斯)
    -c, --cover             封面图路径
    -s, --source-url        原文链接 (默认: https://openclaw.ai)
    --theme                 主题名称 (默认: default)
    --check-only           仅检查，不推送
    -v, --verbose           显示详细日志

示例:
    python3 publish.py -m article.md -t "我的文章" -a "作者"
    python3 publish.py -m article.md --check-only  # 仅检查
"""

import sys
import os
import re
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from functools import wraps

# 配置路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from skills.article_writer import ArticleWriterSkill
from skills.material_skill import MaterialSkill
from skills.draft_skill import DraftSkill
from skills.image_generator import ImageGeneratorSkill
from skills.content_reviewer import ContentReviewerSkill
from config import Config
from token_manager import TokenManager


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(__name__)


def timer(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logging.debug(f"{func.__name__} 耗时: {elapsed:.2f}s")
        return result
    return wrapper


def parse_args():
    parser = argparse.ArgumentParser(
        description='发布公众号文章',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--markdown', '-m', type=str, help='Markdown 文件路径')
    parser.add_argument('--title', '-t', type=str, help='文章标题')
    parser.add_argument('--author', '-a', type=str, default='贾维斯', help='作者 (默认: 贾维斯)')
    parser.add_argument('--cover', '-c', type=str, help='封面图路径 (可选)')
    parser.add_argument('--source-url', '-s', type=str, default='https://openclaw.ai', help='原文链接')
    parser.add_argument('--theme', type=str, default='default', help='主题名称')
    parser.add_argument('--check-only', action='store_true', help='仅检查，不推送')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    return parser.parse_args()


@timer
def check_markdown_conversion(html: str, markdown: str) -> dict:
    """检查 markdown 转 HTML 的完整性"""
    issues = []

    # 根据原始 markdown 内容决定检查项（更精确的检测）
    has_bold = "**" in markdown or "__" in markdown
    # 斜体：单个 * 但不是 ** 或 *
    has_italic = re.search(r'(?<!\*)\*[^*]+\*(?!\*)', markdown) or re.search(r'(?<!_)__[^_]+__(?!_)', markdown)
    has_code_block = "```" in markdown
    has_quote = re.search(r'^>', markdown, re.MULTILINE)
    # 文字链接：[text](url) 且不是图片 ![text](url)
    has_link = bool(re.search(r'(?<!\[)!?\[[^\]]+\]\([^)]+\)', markdown)) and not all(line.strip().startswith('![') for line in markdown.split('\n') if '](' in line)
    has_image = "!["

    # 只检查原始文档中存在的语法
    checks = [
        (r'<strong>', "加粗", has_bold),
        (r'<em>', "斜体", has_italic),
        (r'<pre[^>]*>', "代码块", has_code_block),
        (r'<blockquote[^>]*>', "引用", has_quote),
        (r'<a[^>]*href=', "链接", has_link),
        (r'<img[^>]*src=', "图片", has_image),
    ]

    for pattern, name, needed in checks:
        if needed and not re.search(pattern, html, re.IGNORECASE):
            issues.append(f"{name}未正确转换")

    return {"passed": len(issues) == 0, "issues": issues}


def check_article_integrity(markdown: str = None, html: str = None,
                           draft_content: str = None, stage: str = "unknown") -> Dict:
    """
    共通的文章完整性检查函数

    在三个检查点调用：
    1. check_article_integrity(markdown=md, stage="markdown") - Markdown 生成后
    2. check_article_integrity(html=html, markdown=md, stage="html") - HTML 转换后
    3. check_article_integrity(draft_content=content, stage="draft") - 草稿上传后

    Returns:
        {"passed": bool, "issues": [], "warnings": [], "stats": {}}
    """
    issues = []
    warnings = []
    stats = {}
    cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"

    # ====== 阶段1: Markdown 检查 ======
    if markdown is not None:
        stats["markdown_length"] = len(markdown)
        stats["markdown_lines"] = len(markdown.split('\n'))

        # 检查标题
        h1_count = len(re.findall(r'^#\s+', markdown, re.MULTILINE))
        h2_count = len(re.findall(r'^##\s+', markdown, re.MULTILINE))
        h3_count = len(re.findall(r'^###\s+', markdown, re.MULTILINE))
        stats["h1_count"] = h1_count
        stats["h2_count"] = h2_count
        stats["h3_count"] = h3_count

        if h1_count == 0:
            issues.append("缺少一级标题 (# 标题)")

        # 检查图片语法
        cover_imgs = re.findall(r'!\[封面\]\(([^)]+)\)', markdown)
        section_imgs = re.findall(r'!\[([^\]]+)\]\(([^)]+)\)', markdown)
        all_imgs = cover_imgs + [path for _, path in section_imgs]

        stats["cover_images"] = len(cover_imgs)
        stats["section_images"] = len(section_imgs)
        stats["total_images"] = len(all_imgs)

        if len(cover_imgs) == 0:
            warnings.append("Markdown 中没有封面图 (![封面](path))")

        # 检查图片文件是否存在（仅检查本地路径）
        missing_images = []
        for img_path in all_imgs:
            if not os.path.isabs(img_path) and not img_path.startswith('http'):
                # 本地路径，检查 cache 目录
                if cache_dir.exists():
                    if not (cache_dir / img_path).exists():
                        missing_images.append(img_path)

        if missing_images:
            warnings.append(f"Markdown 中有 {len(missing_images)} 个图片文件不存在: {missing_images[:3]}...")

        logging.info(f"[{stage}] Markdown 检查: 标题={h1_count}/{h2_count}/{h3_count}, 图片={len(all_imgs)}")

    # ====== 阶段2: HTML 检查 ======
    if html is not None:
        stats["html_length"] = len(html)

        # 检查 HTML 标签完整性
        if not html.strip().startswith('<div'):
            issues.append("HTML 内容不是以 <div> 开头")

        # 检查图片标签
        img_tags = re.findall(r'<img[^>]*>', html)
        stats["html_images"] = len(img_tags)

        # 检查图片 src 是否为空
        empty_src = [img for img in img_tags if re.search(r'<img\s+[^>]*>', img) and 'src=' not in img]
        broken_images = [img for img in img_tags if 'src=""' in img or "src=''" in img]

        if empty_src:
            issues.append(f"HTML 中有 {len(empty_src)} 个图片没有 src 属性 (如 <img />)")
        if broken_images:
            issues.append(f"HTML 中有 {len(broken_images)} 个图片 src 为空")

        # 检查是否有外部 URL 图片
        external_images = re.findall(r'<img src="(http[^\"]+)"', html)
        stats["external_images"] = len(external_images)

        # 检查 local URL 图片（需要上传的）
        local_images = re.findall(r'<img src="([^h][^t][^t][^p][^:][^/][^/].+?)"', html)
        stats["local_images"] = len(local_images)

        if len(local_images) > 0 and len(external_images) == 0:
            warnings.append(f"HTML 中有 {len(local_images)} 个本地图片未上传到微信")

        # 检查格式标签
        has_strong = bool(re.search(r'<strong>', html))
        has_em = bool(re.search(r'<em>', html))
        has_pre = bool(re.search(r'<pre', html))
        has_blockquote = bool(re.search(r'<blockquote', html))

        stats["has_bold"] = has_strong
        stats["has_italic"] = has_em
        stats["has_code"] = has_pre
        stats["has_quote"] = has_blockquote

        logging.info(f"[{stage}] HTML 检查: 图片={len(img_tags)} (空src={len(empty_src)}, 本地={len(local_images)}, 外部={len(external_images)})")

    # ====== 阶段3: 草稿内容检查 ======
    if draft_content is not None:
        stats["draft_length"] = len(draft_content)

        # 检查图片标签
        img_tags = re.findall(r'<img[^>]*>', draft_content)
        stats["draft_images"] = len(img_tags)

        # 检查空 src
        empty_src = [img for img in img_tags if 'src=' not in img]
        broken_images = [img for img in img_tags if 'src=""' in img or "src=''" in img or re.search(r'src=" *$"', img)]

        if empty_src:
            issues.append(f"草稿中有 {len(empty_src)} 个图片没有 src 属性 (如 <img />)")
        if broken_images:
            issues.append(f"草稿中有 {len(broken_images)} 个图片 src 为空")

        # 检查外部 URL（微信使用 data-src 或 src）
        data_src_images = re.findall(r'<img[^>]*data-src="(https?://[^"]+)"', draft_content)
        external_images = re.findall(r'<img src="(https?://[^"]+)"', draft_content)
        all_external = data_src_images + external_images

        stats["draft_external_images"] = len(all_external)
        stats["draft_src_images"] = len(external_images)
        stats["draft_data_src_images"] = len(data_src_images)

        if len(all_external) == 0 and len(img_tags) > 0:
            warnings.append("草稿中没有外部 URL 图片，可能未上传到微信")

        # 检查图片 URL 是否可访问（针对外部 URL）
        if all_external:
            import urllib.request
            bad_urls = []
            for url in all_external[:6]:  # 最多检查6张
                try:
                    req = urllib.request.Request(url, method='HEAD')
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        if resp.status != 200:
                            bad_urls.append(f"{url[:60]}... (HTTP {resp.status})")
                except Exception as e:
                    bad_urls.append(f"{url[:60]}... ({type(e).__name__})")
            if bad_urls:
                issues.append(f"有 {len(bad_urls)} 个图片 URL 无效或无法访问: {bad_urls[:3]}{'...' if len(bad_urls) > 3 else ''}")

        # 检查编码
        try:
            draft_content.encode('utf-8')
            stats["encoding_ok"] = True
        except UnicodeEncodeError:
            issues.append("草稿内容编码异常")

        # 检查乱码
        if '�' in draft_content:
            warnings.append("草稿内容包含乱码字符")

        logging.info(f"[{stage}] 草稿检查: 图片={len(img_tags)}, 空src={len(empty_src)}, 外部URL={len(external_images)}")

    # 返回结果
    passed = len(issues) == 0

    result = {
        "passed": passed,
        "stage": stage,
        "issues": issues,
        "warnings": warnings,
        "stats": stats
    }

    # 打印检查结果
    if issues:
        logging.error(f"❌ [{stage}] 检查未通过:")
        for issue in issues:
            logging.error(f"   - {issue}")

    if warnings:
        logging.warning(f"⚠️ [{stage}] 检查警告:")
        for warn in warnings:
            logging.warning(f"   - {warn}")

    if passed and not warnings:
        logging.info(f"✅ [{stage}] 检查通过")

    return result


@timer
def insert_images_to_content(html: str, material_skill, dry_run: bool = False) -> Tuple[str, List[str]]:
    """处理文章中的图片：上传到微信并替换 HTML 中的图片路径"""
    import re
    from pathlib import Path

    img_pattern = r'<img src="([^"]+)"[^>]*>'
    matches = re.findall(img_pattern, html)

    if not matches:
        return html, []

    # 图片缓存目录
    cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"

    processed = []
    for img_path in matches:
        if img_path in processed:
            continue

        # 检查文件是否存在
        actual_path = img_path
        if not os.path.exists(img_path):
            # 尝试在 cache 目录查找
            if cache_dir.exists():
                potential = cache_dir / img_path
                if potential.exists():
                    actual_path = str(potential)

        if not os.path.exists(actual_path):
            # 外部 URL：下载后上传到微信
            if img_path.startswith('http://') or img_path.startswith('https://'):
                try:
                    import tempfile
                    import urllib.request
                    ext = os.path.splitext(img_path.split('?')[0])[1] or '.jpg'
                    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                        tmp_path = tmp.name
                    urllib.request.urlretrieve(img_path, tmp_path)
                    result = material_skill.upload_image(tmp_path)
                    wechat_url = result.get('url')
                    if wechat_url:
                        html = html.replace(f'<img src="{img_path}"', f'<img src="{wechat_url}"')
                        logging.info(f"✓ 外部图片上传成功: {img_path[:60]}...")
                    else:
                        logging.warning(f"✗ 外部图片上传失败: {img_path[:60]}")
                    os.unlink(tmp_path)
                    processed.append(img_path)
                    continue
                except Exception as e:
                    logging.error(f"✗ 外部图片处理失败: {img_path[:60]}, 错误: {e}")
                    processed.append(img_path)
                    continue
            logging.warning(f"图片文件不存在: {img_path}, 跳过")
            continue

        try:
            if dry_run:
                logging.info(f"[dry-run] 会上传图片: {actual_path}")
                processed.append(img_path)
                continue

            result = material_skill.upload_image(actual_path)
            wechat_url = result.get('url')

            if wechat_url:
                # 替换图片路径
                html = html.replace(f'<img src="{img_path}"', f'<img src="{wechat_url}"')
                logging.info(f"✓ 图片上传成功: {os.path.basename(actual_path)}")
                processed.append(img_path)
            else:
                logging.warning(f"✗ 图片上传失败，无 URL: {img_path}")
        except Exception as e:
            logging.error(f"✗ 处理图片失败: {img_path}, 错误: {e}")

    return html, processed


@timer
def find_cover_image(theme: str, title: str = "") -> Optional[str]:
    """自动查找或生成封面图"""
    cache_dir = Path.home() / ".cache" / "wechat-mp-auto" / "images"

    # 如果有标题，尝试从图库搜横向封面
    if title:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from skills.image_generator import ImageGeneratorSkill
            img_gen = ImageGeneratorSkill()
            # 优先用标题搜横向封面
            images = img_gen._search_all(title, count=5)
            for img_info in images:
                path = img_gen._download_image(img_info, "cover",
                                              max_width=900, max_height=500)
                if path:
                    logging.info(f"图库封面搜索成功: {path}")
                    return path
        except Exception as e:
            logging.warning(f"图库封面搜索失败: {e}")

    # fallback：从缓存选大文件（>500KB），跳过缩略图
    if cache_dir.exists():
        covers = [p for p in cache_dir.glob("cover_*.jpg")
                  if "_thumb" not in p.name and p.stat().st_size > 500000]
        if covers:
            latest = max(covers, key=lambda p: p.stat().st_mtime)
            return str(latest)
        all_covers = [p for p in cache_dir.glob("cover_*.jpg")
                      if p.stat().st_size > 500000]
        if all_covers:
            latest = max(all_covers, key=lambda p: p.stat().st_mtime)
            return str(latest)

    return None


@timer
def generate_cover_image(title: str, img_generator: ImageGeneratorSkill) -> Optional[str]:
    """生成封面图"""
    try:
        logging.info(f"尝试自动生成封面图: {title[:30]}...")
        cover_path = img_generator.generate_cover(title, [])
        if cover_path:
            logging.info(f"✓ 封面图生成成功: {cover_path}")
            return cover_path
    except Exception as e:
        logging.error(f"✗ 封面图生成失败: {e}")
    return None


def validate_args(args) -> bool:
    """验证命令行参数"""
    if not args.markdown:
        default_md = '/tmp/openclaw-final.md'
        if os.path.exists(default_md):
            args.markdown = default_md
            logging.info(f"使用默认 Markdown 文件: {default_md}")
        else:
            logging.error("请指定 --markdown 参数")
            return False

    if not os.path.exists(args.markdown):
        logging.error(f"Markdown 文件不存在: {args.markdown}")
        return False

    if not args.title:
        args.title = os.path.splitext(os.path.basename(args.markdown))[0]
        logging.info(f"使用文件名作为标题: {args.title}")

    return True


@timer
def initialize_components() -> Dict:
    """初始化组件"""
    config = Config()
    app_id, app_secret = config.get_credentials()
    token_mgr = TokenManager(app_id, app_secret)

    return {
        'writer': ArticleWriterSkill(),
        'material': MaterialSkill(token_mgr),
        'draft': DraftSkill(token_mgr),
        'img_generator': ImageGeneratorSkill(),
    }


@timer
def publish_article(args, components) -> bool:
    """发布文章主流程"""
    # 1. 读取 Markdown
    logging.info(f"读取 Markdown: {args.markdown}")
    with open(args.markdown, 'r', encoding='utf-8') as f:
        markdown = f.read()
    logging.info(f"✓ 读取成功，共 {len(markdown)} 字符")

    # ====== 检查点1: Markdown 生成/读取后 ======
    logging.info("=" * 50)
    logging.info("【检查点1】Markdown 完整性检查")
    logging.info("=" * 50)
    md_check = check_article_integrity(markdown=markdown, stage="markdown")

    # ====== 内容审核检查 ======
    logging.info("=" * 50)
    logging.info("【内容审核】合规性 & 重复度检查")
    logging.info("=" * 50)

    # 初始化内容审核器
    content_reviewer = ContentReviewerSkill()
    article = {"markdown": markdown, "content": markdown}
    review_result = content_reviewer.review_article(article)

    if review_result.get("passed"):
        logging.info("✅ 内容审核通过")
    else:
        logging.error("❌ 内容审核未通过:")
        for issue in review_result.get("issues", []):
            severity = issue.get("severity", "unknown")
            msg = issue.get("message", "")
            logging.error(f"   [{severity}] {msg}")

    # 检查违规内容
    prohibited = review_result.get("prohibited", {})
    if prohibited.get("has_violations"):
        violations = prohibited.get("violations", [])
        logging.error(f"❌ 发现 {len(violations)} 个违规词: {[v.get('word') for v in violations]}")
        if not args.check_only:
            logging.error("请修改内容后重试")
            return False

    # 检查重复度
    plagiarism = review_result.get("plagiarism", {})
    similarity = plagiarism.get("similarity", 0)
    is_duplicated = plagiarism.get("is_duplicated", False)
    if is_duplicated or similarity > 30:
        logging.warning(f"⚠️ 文章重复度较高: {similarity}%")

    logging.info(f"   - 重复度: {similarity}%")
    logging.info(f"   - 敏感词检查: {'通过' if not prohibited.get('has_violations') else '未通过'}")

    # 2. 转换为 HTML
    logging.info("转换 Markdown -> HTML...")
    html = components['writer'].convert_to_html(markdown, args.theme)
    logging.info("✓ 转换完成")

    # ====== 检查点2: HTML 转换后 ======
    logging.info("=" * 50)
    logging.info("【检查点2】HTML 完整性检查")
    logging.info("=" * 50)
    html_check = check_article_integrity(markdown=markdown, html=html, stage="html")

    # 3. 检查转换质量（保留原有检查）
    logging.info("检查转换质量...")
    check_result = check_markdown_conversion(html, markdown)
    if not check_result["passed"]:
        logging.warning("⚠️ 转换检查发现问题:")
        for issue in check_result["issues"]:
            logging.warning(f"  - {issue}")
        if not args.check_only:
            logging.warning("请修复后再推送，5秒后继续...")
            import time
            time.sleep(5)
    else:
        logging.info("✓ 转换检查通过")

    # 4. 处理封面图
    cover_path = args.cover or find_cover_image(args.theme, args.title)
    if not cover_path:
        logging.info("未找到封面图，尝试自动生成...")
        cover_path = generate_cover_image(args.title, components['img_generator'])

    if not cover_path or not os.path.exists(cover_path):
        logging.error("✗ 封面图不可用，请使用 --cover 指定")
        return False

    logging.info(f"✓ 使用封面图: {os.path.basename(cover_path)}")

    # 5. 处理文章插图
    logging.info("处理文章插图...")
    html, processed_images = insert_images_to_content(html, components['material'], args.check_only)
    if processed_images:
        logging.info(f"✓ 已处理 {len(processed_images)} 张插图")
    else:
        logging.info("○ 无需处理的插图")

    if args.check_only:
        logging.info("检查模式完成，未推送")
        return True

    # 6. 上传封面图
    logging.info("上传封面图...")
    cover_result = components['material'].upload_image(cover_path)
    media_id = cover_result.get('media_id')
    cover_wechat_url = cover_result.get('url', '')
    logging.info(f"✓ 封面上传成功: {cover_wechat_url[:40]}...")

    # 6.1 替换 HTML 中所有封面图占位符（全局替换，包括章节图）
    if cover_wechat_url:
        count = html.count('src="cover_image_url"')
        html = html.replace('src="cover_image_url"', f'src="{cover_wechat_url}"')
        logging.info(f"✓ 封面图占位符已替换（{count}处）")
    else:
        logging.warning("⚠️ 封面图无 URL，占位符未替换")

    # 6.2 替换章节图占位符（暂时用封面图替代，保证草稿完整展示）
    if cover_wechat_url:
        section_placeholder_pattern = re.compile(r'src="([^"]+_url)"')
        section_placeholders = section_placeholder_pattern.findall(html)
        if section_placeholders:
            for ph in section_placeholders:
                html = html.replace(f'src="{ph}"', f'src="{cover_wechat_url}"')
            logging.info(f"✓ 章节图占位符已替换为封面图（{len(section_placeholders)}处）")

    # 7. 添加 meta 并保存
    html = '<meta charset="utf-8">\n' + html
    output_html = args.markdown.replace('.md', '.html')
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)
    logging.info(f"✓ HTML 已保存: {output_html}")

    # 8. 创建草稿
    logging.info("创建草稿...")
    article = {
        'title': args.title,
        'author': args.author,
        'content': html,
        'thumb_media_id': media_id,
        'content_source_url': args.source_url
    }

    result = components['draft'].create_draft([article])
    draft_id = result.get('media_id')

    # ====== 检查点3: 草稿上传后 ======
    logging.info("=" * 50)
    logging.info("【检查点3】草稿完整性检查")
    logging.info("=" * 50)

    # 获取刚创建的草稿内容进行验证
    try:
        draft_detail = components['draft'].get_draft(draft_id)
        draft_content = draft_detail.get('news_item', [{}])[0].get('content', '')
        draft_check = check_article_integrity(draft_content=draft_content, stage="draft")
    except Exception as e:
        logging.warning(f"获取草稿详情失败，跳过检查: {e}")

    logging.info("=" * 50)
    logging.info("🎉 发布完成!")
    logging.info(f"  草稿 ID: {draft_id}")
    logging.info(f"  标题: {args.title}")
    logging.info(f"  作者: {args.author}")
    logging.info("=" * 50)

    return True


def main():
    args = parse_args()
    logger = setup_logging(args.verbose)

    logging.info("微信公众号文章发布工具")
    logging.info("=" * 50)

    # 验证参数
    if not validate_args(args):
        sys.exit(1)

    # 初始化组件
    logging.info("初始化组件...")
    components = initialize_components()

    # 发布文章
    success = publish_article(args, components)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
