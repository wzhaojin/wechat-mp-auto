#!/usr/bin/env python3
"""测试 wechat-mp-auto 的 markdown 转换和插图功能"""
import sys
sys.path.insert(0, '/Users/wzj/.openclaw/workspace/skills/wechat-mp-auto/src')

from skills.article_writer import ArticleWriterSkill
import re

writer = ArticleWriterSkill()

# 测试 markdown
test_md = """# 测试标题

这是一段普通文本，包含**加粗**和*斜体*，还有__双下划线加粗__和_单下划线斜体_。

## 二级标题

### 三级标题

这里是行内代码 `echo hello` 的示例。

```
# 代码块测试
def hello():
    print("Hello World")
```

> 这是一段引用内容
> 可以换行

- 无序列表项 1
- 无序列表项 2

1. 有序列表项 1
2. 有序列表项 2

[链接文字](https://example.com)

![图片描述](test.jpg)

"""

print("=" * 50)
print("测试1: Markdown 转 HTML 完整性")
print("=" * 50)

html = writer.convert_to_html(test_md, 'default')

# 检查各项转换
checks = {
    "加粗 **": "**加粗**" in test_md and "<strong>加粗</strong>" in html,
    "加粗 __": "__双下划线加粗__" in test_md and "<strong>双下划线加粗</strong>" in html,
    "斜体 *": "*斜体*" in test_md and "<em>斜体</em>" in html,
    "斜体 _": "_单下划线斜体_" in test_md and "<em>单下划线斜体</em>" in html,
    "行内代码": "`echo hello`" in test_md and "<code" in html,
    "代码块": "```" in test_md and "<pre>" in html,
    "引用 >": ">" in test_md and "<blockquote>" in html,
    "无序列表": "- " in test_md and "•" in html,
    "有序列表": "1. " in test_md and "1." in html,
    "链接": "[链接文字]" in test_md and "<a href=" in html,
    "图片": "![图片描述]" in test_md and '<img src="' in html,
}

all_passed = True
for name, passed in checks.items():
    status = "✓" if passed else "✗"
    print(f"  {status} {name}")
    if not passed:
        all_passed = False

print()
print("=" * 50)
print("测试2: 检查 HTML 中是否有残留 markdown 语法")
print("=" * 50)

# 检查是否有未转换的 markdown 符号
residual_patterns = [
    (r'\*\*[^*]+\*\*', "原始加粗 ** 未转义"),
    (r'__[^_]+__', "原始加粗 __ 未转义"),
    (r'(?<!\*)\*(?!\*)[^*]+(?!\*)', "原始斜体 * 未转义"),
]

issues = []
for pattern, desc in residual_patterns:
    if re.search(pattern, html):
        issues.append(desc)

if issues:
    print("  ✗ 发现问题:")
    for issue in issues:
        print(f"    - {issue}")
else:
    print("  ✓ 没有残留的 markdown 语法")

print()
print("=" * 50)
print("测试3: 检查函数测试")
print("=" * 50)

# 导入并测试检查函数
exec(open('/Users/wzj/.openclaw/workspace/skills/wechat-mp-auto/src/publish.py').read().split('def check_markdown_conversion')[1].split('def insert_images')[0])

check_result = check_markdown_conversion(html, test_md)
print(f"  检查结果: {'通过' if check_result['passed'] else '发现 ' + str(len(check_result['issues'])) + ' 个问题'}")
if check_result['issues']:
    for issue in check_result['issues'][:3]:
        print(f"    - {issue}")

print()
print("=" * 50)
print("测试结果汇总")
print("=" * 50)
print(f"  转换完整性: {'✓ 通过' if all_passed else '✗ 失败'}")
print(f"  无残留语法: {'✓ 通过' if not issues else '✗ 失败'}")
print(f"  检查函数: {'✓ 通过' if check_result['passed'] else '⚠️ 需手动确认'}")
