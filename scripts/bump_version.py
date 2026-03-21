#!/usr/bin/env python3
"""
版本号同步脚本 - 每次发布前运行此脚本更新版本号

用法:
    python scripts/bump_version.py 0.1.0 "新增xxx功能"
    python scripts/bump_version.py  # 不带参数则读取 src/_version.py 打印当前版本

同时更新以下文件:
    src/_version.py        - 单一数据源
    pyproject.toml        - build metadata
    metadata.json          - ClawHub metadata
    SKILL.md              - AI 编排文档
    README.md              - Badge
    CHANGELOG.md          - 变更记录
"""

import sys
import os
import re
import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent


def get_current_version():
    version_file = REPO_DIR / "src" / "_version.py"
    if version_file.exists():
        content = version_file.read_text()
        m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            return m.group(1)
    return None


def bump_version(new_version: str, changelog_entry: str = ""):
    """更新所有文件中的版本号"""
    changes = []

    # 1. src/_version.py
    vf = REPO_DIR / "src" / "_version.py"
    old_content = vf.read_text()
    new_content = re.sub(r'VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{new_version}"', old_content)
    if old_content != new_content:
        vf.write_text(new_content)
        changes.append("src/_version.py")

    # 2. pyproject.toml
    pt = REPO_DIR / "pyproject.toml"
    old_content = pt.read_text()
    new_content = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', old_content)
    if old_content != new_content:
        pt.write_text(new_content)
        changes.append("pyproject.toml")

    # 3. metadata.json
    mj = REPO_DIR / "metadata.json"
    old_content = mj.read_text()
    new_content = re.sub(r'"version":\s*"[^"]+"', f'"version": "v{new_version}"', old_content)
    if old_content != new_content:
        mj.write_text(new_content)
        changes.append("metadata.json")

    # 4. SKILL.md
    sm = REPO_DIR / "SKILL.md"
    old_content = sm.read_text()
    new_content = re.sub(r'\*\*版本\*\*:\s*v[\d.]+', f'**版本**: v{new_version}', old_content)
    if old_content != new_content:
        sm.write_text(new_content)
        changes.append("SKILL.md")

    # 5. README.md badge
    rm = REPO_DIR / "README.md"
    old_content = rm.read_text()
    new_content = re.sub(
        r'\[!\[Version\]\(https://img\.shields\.io/badge/version-v\)[\d.]+\.png\)\]\(SKILL\.md\)',
        f'[![Version](https://img.shields.io/badge/version-v{new_version}-blue)](SKILL.md)',
        old_content
    )
    if old_content != new_content:
        rm.write_text(new_content)
        changes.append("README.md")

    # 6. CHANGELOG.md - 追加新版本
    cl = REPO_DIR / "CHANGELOG.md"
    today = datetime.date.today().strftime("%Y-%m-%d")
    date_str = today

    new_entry = f"""## [{new_version}] - {date_str}

{changelog_entry}
"""
    old_content = cl.read_text()
    # 在 "## [Unreleased]" 或 "## [" 之后插入，或在顶部追加
    if changelog_entry:
        if old_content.startswith("# Changelog"):
            # 找到第一个 ## [x.x.x] 之前插入
            first_version_pos = re.search(r'^## \[', old_content, re.MULTILINE)
            if first_version_pos:
                insert_pos = first_version_pos.start()
                new_content = old_content[:insert_pos] + new_entry.strip() + "\n\n" + old_content[insert_pos:]
            else:
                new_content = old_content + "\n\n" + new_entry
        else:
            new_content = old_content + "\n\n" + new_entry

        if old_content != new_content:
            cl.write_text(new_content)
            changes.append("CHANGELOG.md (新增版本条目)")

    return changes


def check_version_consistency():
    """检查所有文件的版本号是否一致，返回 (一致, 当前版本, 不一致文件列表)"""
    versions = {}

    # src/_version.py
    version_file = REPO_DIR / "src" / "_version.py"
    if version_file.exists():
        content = version_file.read_text()
        m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            versions["src/_version.py"] = m.group(1)

    # pyproject.toml
    pt = REPO_DIR / "pyproject.toml"
    if pt.exists():
        content = pt.read_text()
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            versions["pyproject.toml"] = m.group(1)

    # metadata.json
    mj = REPO_DIR / "metadata.json"
    if mj.exists():
        content = mj.read_text()
        m = re.search(r'"version":\s*"([^"]+)"', content)
        if m:
            versions["metadata.json"] = m.group(1).lstrip("v")

    # SKILL.md
    sm = REPO_DIR / "SKILL.md"
    if sm.exists():
        content = sm.read_text()
        m = re.search(r'\*\*版本\*\*:\s*v([\d.]+)', content)
        if m:
            versions["SKILL.md"] = m.group(1)

    # README.md
    rm = REPO_DIR / "README.md"
    if rm.exists():
        content = rm.read_text()
        m = re.search(r'version-v([\d.]+)-blue', content)
        if m:
            versions["README.md"] = m.group(1)

    unique_versions = set(versions.values())
    inconsistent = [f for f, v in versions.items() if v not in unique_versions]

    return len(unique_versions) == 1, list(unique_versions)[0] if unique_versions else None, inconsistent


def main():
    if len(sys.argv) < 2:
        # 无参数：检查一致性
        consistent, version, inconsistent = check_version_consistency()
        print(f"当前版本: {version}")
        if consistent:
            print("✅ 所有文件版本号一致")
            sys.exit(0)
        else:
            print(f"❌ 版本号不一致，涉事文件: {inconsistent}")
            sys.exit(1)

    new_version = sys.argv[1]
    changelog_entry = sys.argv[2] if len(sys.argv) > 2 else ""

    # 版本号格式检查
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(f"❌ 版本号格式错误，应为 x.y.z，例如 0.0.9，实际: {new_version}")
        sys.exit(1)

    current = get_current_version()
    if current == new_version:
        print(f"❌ 版本号未变化，当前已是 {new_version}")
        sys.exit(1)

    print(f"🔄 {current} → {new_version}")
    changes = bump_version(new_version, changelog_entry)
    for f in changes:
        print(f"  ✅ 更新: {f}")

    # 验证一致性
    consistent, version, inconsistent = check_version_consistency()
    if consistent:
        print(f"\n✅ 版本号已全部更新为 {version}，所有文件一致")
    else:
        print(f"\n❌ 更新后仍有文件版本不一致: {inconsistent}")
        sys.exit(1)


if __name__ == "__main__":
    main()
