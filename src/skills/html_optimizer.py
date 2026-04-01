"""
微信公众号自动化 - HTML优化技能
提供HTML压缩、清理和预览检查功能，确保推送到微信公众号草稿箱的内容能够正确显示。

从 wechat-allauto-gzh 项目借鉴并增强：
- 分级警告系统（INFO/WARNING/ERROR/CRITICAL）
- 压缩率报告
"""

import re
import html as html_module
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class HTMLWarningLevel(Enum):
    """HTML警告级别"""
    INFO = "info"           # 信息提示
    WARNING = "warning"     # 警告（可能影响显示）
    ERROR = "error"         # 错误（很可能导致显示异常）
    CRITICAL = "critical"   # 严重错误（必定导致显示异常）


@dataclass
class HTMLWarning:
    """HTML警告信息"""
    level: HTMLWarningLevel
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "level": self.level.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "suggestion": self.suggestion
        }


@dataclass
class HTMLCheckResult:
    """HTML检查结果"""
    is_valid: bool
    warnings: List[HTMLWarning]
    original_size: int
    compressed_size: int
    compression_ratio: float
    
    def get_errors(self) -> List[HTMLWarning]:
        """获取错误级别的警告"""
        return [w for w in self.warnings if w.level in (HTMLWarningLevel.ERROR, HTMLWarningLevel.CRITICAL)]
    
    def get_summary(self) -> Dict:
        """获取检查摘要"""
        levels = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for w in self.warnings:
            levels[w.level.value] += 1
        
        return {
            "is_valid": self.is_valid,
            "compression_ratio": round(self.compression_ratio, 2),
            "size_original": self.original_size,
            "size_compressed": self.compressed_size,
            "warnings": levels,
            "has_errors": len(self.get_errors()) > 0
        }


class HTMLOptimizer:
    """HTML优化器"""
    
    # 微信公众号不支持的标签
    UNSUPPORTED_TAGS: set = {
        'script', 'iframe', 'embed', 'object', 'form', 'input', 
        'textarea', 'select', 'button', 'canvas', 'svg', 'video', 'audio'
    }
    
    # 微信公众号不推荐的属性
    UNRECOMMENDED_ATTRS: set = {
        'style', 'class', 'id', 'onclick', 'onload', 'onerror', 
        'data-*', 'aria-*', 'role'
    }
    
    # 微信公众号支持但需要注意的标签
    SPECIAL_TAGS: Dict[str, str] = {
        'img': '图片标签需要确保src有效且图片已上传到微信素材库',
        'a': '链接标签需要确保href为白名单域名',
        'br': '换行标签在微信中表现可能与预期不同',
    }
    
    def __init__(self, remove_comments: bool = True, 
                 remove_empty_tags: bool = True,
                 minify_inline: bool = True):
        """
        初始化HTML优化器
        
        Args:
            remove_comments: 是否移除HTML注释
            remove_empty_tags: 是否移除空标签
            minify_inline: 是否压缩内联样式
        """
        self.remove_comments = remove_comments
        self.remove_empty_tags = remove_empty_tags
        self.minify_inline = minify_inline
    
    def compress(self, html_content: str) -> str:
        """
        压缩HTML内容
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            压缩后的HTML
        """
        result = html_content
        
        # 1. 移除HTML注释
        if self.remove_comments:
            result = re.sub(r'<!--.*?-->', '', result, flags=re.DOTALL)
        
        # 2. 压缩空白字符
        result = re.sub(r'>\s+<', '><', result)
        result = re.sub(r'\s+', ' ', result)
        
        # 3. 压缩内联样式
        if self.minify_inline:
            result = re.sub(
                r'style="([^"]*)"',
                lambda m: 'style="' + re.sub(r'\s*:\s*', ':', 
                                            re.sub(r'\s*;\s*', ';',
                                                   m.group(1).strip())) + '"',
                result,
                flags=re.IGNORECASE
            )
        
        # 4. 移除空标签（保留img、br等特殊标签）
        if self.remove_empty_tags:
            empty_tags = r'<(?!img|br|hr|input|meta|link|area|base|col|embed|param|source|track|wbr)[^>]+?>\s*</[^>]+?>'
            result = re.sub(empty_tags, '', result, flags=re.IGNORECASE | re.DOTALL)
        
        # 5. 移除HTML实体编码的冗余
        result = re.sub(r'&#x20;|&#32;', ' ', result)
        
        # 6. 移除制表符和换行符
        result = result.replace('\t', ' ').replace('\n', ' ')
        
        # 7. 最终清理
        result = result.strip()
        
        return result
    
    def check(self, html_content: str) -> HTMLCheckResult:
        """
        检查HTML内容是否适合微信公众号
        
        Args:
            html_content: HTML内容
            
        Returns:
            检查结果
        """
        warnings: List[HTMLWarning] = []
        original_size = len(html_content)
        
        # 压缩HTML
        compressed = self.compress(html_content)
        compressed_size = len(compressed)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # 检查不支持的标签
        for tag in self.UNSUPPORTED_TAGS:
            pattern = f'<{tag}[^>]*>'
            matches = list(re.finditer(pattern, html_content, re.IGNORECASE))
            if matches:
                for match in matches[:3]:
                    warnings.append(HTMLWarning(
                        level=HTMLWarningLevel.ERROR,
                        message=f"发现不支持的标签 <{tag}>",
                        suggestion=f"移除<{tag}>标签或使用其他方式实现相同效果",
                        line=html_content[:match.start()].count('\n') + 1
                    ))
                if len(matches) > 3:
                    warnings.append(HTMLWarning(
                        level=HTMLWarningLevel.ERROR,
                        message=f"发现 {len(matches)} 个不支持的 <{tag}> 标签",
                        suggestion="请检查并移除所有不支持的标签"
                    ))
        
        # 检查图片标签
        img_count = len(re.findall(r'<img[^>]*>', html_content, re.IGNORECASE))
        if img_count > 0:
            warnings.append(HTMLWarning(
                level=HTMLWarningLevel.INFO,
                message=f"发现 {img_count} 个图片标签",
                suggestion="确保所有图片已上传到微信素材库，且src引用正确"
            ))
        
        # 检查链接标签
        a_tags = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>', html_content, re.IGNORECASE)
        if a_tags:
            external_links = [href for href in a_tags if not href.startswith('#') and not href.startswith('javascript:')]
            if external_links:
                warnings.append(HTMLWarning(
                    level=HTMLWarningLevel.WARNING,
                    message=f"发现 {len(external_links)} 个外部链接",
                    suggestion="确保链接域名已在微信公众平台白名单中"
                ))
        
        # 检查HTML大小
        if original_size > 100000:
            warnings.append(HTMLWarning(
                level=HTMLWarningLevel.WARNING,
                message=f"HTML内容较大 ({original_size} 字符)",
                suggestion="建议优化内容，微信公众号文章过长可能影响阅读体验"
            ))
        
        # 检查压缩效果
        if compression_ratio > 0.9:
            warnings.append(HTMLWarning(
                level=HTMLWarningLevel.INFO,
                message="HTML压缩率较低，可能已经优化良好",
                suggestion="无需进一步压缩"
            ))
        
        # 检查特殊字符
        special_chars = re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', html_content)
        if special_chars:
            warnings.append(HTMLWarning(
                level=HTMLWarningLevel.ERROR,
                message=f"发现 {len(special_chars)} 个控制字符",
                suggestion="移除所有控制字符，它们可能导致显示异常"
            ))
        
        # 确定是否有效
        errors = [w for w in warnings if w.level in (HTMLWarningLevel.ERROR, HTMLWarningLevel.CRITICAL)]
        is_valid = len(errors) == 0
        
        return HTMLCheckResult(
            is_valid=is_valid,
            warnings=warnings,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio
        )


# 便捷函数
def compress_html(html_content: str, remove_comments: bool = True) -> str:
    """
    快速压缩HTML
    
    Args:
        html_content: 原始HTML
        remove_comments: 是否移除注释
        
    Returns:
        压缩后的HTML
    """
    optimizer = HTMLOptimizer(remove_comments=remove_comments)
    return optimizer.compress(html_content)


def check_html_for_wechat(html_content: str) -> Dict:
    """
    检查HTML是否适合微信公众号
    
    Args:
        html_content: HTML内容
        
    Returns:
        检查结果摘要
        
    Example:
        >>> result = check_html_for_wechat('<p>Hello</p>')
        >>> print(result['is_valid'])
        True
    """
    optimizer = HTMLOptimizer()
    result = optimizer.check(html_content)
    return result.get_summary()
