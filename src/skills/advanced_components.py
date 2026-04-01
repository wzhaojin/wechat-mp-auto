"""
高级组件模块 - 提供微信公众号高级样式组件
包括: release, grid, timeline, steps, compare, focus
"""

import re


class AdvancedComponents:
    """高级组件渲染器"""

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """将hex颜色转换为rgba"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f'rgba({r},{g},{b},{alpha})'
        return hex_color

    @staticmethod
    def _get_contrast_color(hex_color: str) -> str:
        """获取对比色（黑色或白色）"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return '#ffffff' if luminance < 0.5 else '#333333'
        return '#333333'

    def _render_release(self, content: str, params: str, primary: str) -> str:
        """渲染 release 组件：文摘卡片"""
        param_parts = params.strip().split() if params.strip() else []
        main_title = param_parts[0] if len(param_parts) >= 1 else "WEEKLY SELECTION"
        sub_title = param_parts[1] if len(param_parts) >= 2 else "不仅仅是文字"
        text_color = self._get_contrast_color(primary)

        inner_html = content
        inner_html = re.sub(r'^# (.+)$', f'<div style="font-size: 20px; font-weight: bold; color: #333; margin: 12px 0; line-height: 1.4;">\\1</div>', inner_html, flags=re.MULTILINE)
        inner_html = re.sub(r'\*\*(.+?)\*\*', f'<span style="background-color: {primary}33; color: {primary}; padding: 2px 6px; border-radius: 4px; display: inline-block;">\\1</span>', inner_html)

        return f'''<section style="background-color: #fcf9f2; border-radius: 12px; margin: 24px 0; border: 1px solid #f0ebe1; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="padding: 24px 20px 60px 20px; position: relative;">
    <div style="font-size: 11px; font-weight: bold; color: {primary}; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 16px;">{main_title}</div>
    <div style="font-size: 13px; color: #999; margin-bottom: 8px;">{sub_title}</div>
    {inner_html}
  </div>
  <div style="background-color: {primary}; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between;">
    <span style="color: {text_color}; font-weight: bold; font-size: 14px;">文摘</span>
    <div>
      <span style="color: rgba(255,255,255,0.9); font-size: 11px; border: 1px solid rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 4px; margin-left: 6px;">可共赏</span>
      <span style="color: rgba(255,255,255,0.9); font-size: 11px; border: 1px solid rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 4px; margin-left: 6px;">慢阅读</span>
      <span style="color: rgba(255,255,255,0.9); font-size: 11px; border: 1px solid rgba(255,255,255,0.4); padding: 2px 6px; border-radius: 4px; margin-left: 6px;">治愈系</span>
    </div>
  </div>
</section>'''

    def _render_grid(self, content: str, params: str, primary: str) -> str:
        """渲染 grid 组件：多列卡片"""
        cards = [c.strip() for c in content.split("---") if c.strip()]
        grid_html = '<section style="display: flex; justify-content: space-between; align-items: stretch; margin: 20px 0; overflow-x: auto; padding-bottom: 8px; gap: 8px;">'

        for i, card in enumerate(cards):
            is_first = i == 0
            bg = primary if is_first else "#fcfcfc"
            color = self._get_contrast_color(primary) if is_first else "#333"
            border = "none" if is_first else "1px solid #f0f0f0"

            lines = card.split("\n")
            sub_title = lines[0] if lines else ""
            main_text = "<br>".join(lines[1:]) if len(lines) > 1 else ""

            grid_html += f'''<div style="flex: 1; min-width: 110px; background-color: {bg}; border-radius: 8px; padding: 12px; border: {border}; box-sizing: border-box;">
  <div style="font-size: 10px; font-weight: bold; color: {'rgba(255,255,255,0.7)' if is_first else '#aaa'}; margin-bottom: 6px;">PART 0{i + 1}</div>
  <div style="font-size: 14px; font-weight: bold; color: {color}; line-height: 1.4; margin-bottom: 6px;">{sub_title}</div>
  <div style="font-size: 11px; color: {'rgba(255,255,255,0.9)' if is_first else '#777'}; line-height: 1.5;">{main_text}</div>
</div>'''

        grid_html += '</section>'
        return grid_html

    def _render_timeline(self, content: str, params: str, primary: str) -> str:
        """渲染 timeline 组件：时间线"""
        items = [item.strip() for item in content.split("---") if item.strip()]
        timeline_html = f'''<section style="margin: 24px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow-x: auto;">
  <div style="position: relative; padding-left: 24px;">'''

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            lines = item.split("\n", 1)
            time_text = lines[0].strip() if lines else ""
            desc_text = lines[1].strip() if len(lines) > 1 else ""
            line_style = "" if is_last else f"border-left: 2px solid {primary}40;"

            timeline_html += f'''<div style="position: relative; margin-bottom: {'0' if is_last else '20px'}; {line_style}">
  <div style="position: absolute; left: -28px; top: 4px; width: 12px; height: 12px; border-radius: 50%; background-color: {primary}; box-shadow: 0 0 0 4px {primary}20;"></div>
  <div style="font-size: 12px; color: {primary}; font-weight: bold; margin-bottom: 4px;">{time_text}</div>
  <div style="font-size: 14px; color: #333; line-height: 1.6;">{desc_text}</div>
</div>'''

        timeline_html += '</div></section>'
        return timeline_html

    def _render_steps(self, content: str, params: str, primary: str) -> str:
        """渲染 steps 组件：步骤流程"""
        items = [item.strip() for item in content.split("---") if item.strip()]
        text_color = self._get_contrast_color(primary)
        steps_html = f'''<section style="margin: 24px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="display: flex; flex-wrap: wrap; gap: 16px;">'''

        for i, item in enumerate(items):
            num = f"0{i + 1}" if i < 9 else str(i + 1)
            lines = item.split("\n", 1)
            step_title = lines[0].strip() if lines else ""
            step_desc = lines[1].strip() if len(lines) > 1 else ""

            steps_html += f'''<div style="flex: 1; min-width: 200px; background-color: {primary}; border-radius: 8px; padding: 16px; box-sizing: border-box;">
  <div style="display: inline-block; background-color: {text_color}; color: {primary}; font-size: 12px; font-weight: bold; padding: 4px 10px; border-radius: 12px; margin-bottom: 12px;">{num}</div>
  <div style="font-size: 16px; font-weight: bold; color: {text_color}; margin-bottom: 8px;">{step_title}</div>
  <div style="font-size: 13px; color: {'rgba(255,255,255,0.85)' if text_color == '#ffffff' else '#666'}; line-height: 1.5;">{step_desc}</div>
</div>'''

        steps_html += '</div></section>'
        return steps_html

    def _render_compare(self, content: str, params: str, primary: str) -> str:
        """渲染 compare 组件：对比布局"""
        parts = [p.strip() for p in content.split("---") if p.strip()]
        while len(parts) < 2:
            parts.append("")

        left_content = parts[0]
        right_content = parts[1]

        return f'''<section style="margin: 24px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="display: flex; gap: 16px; flex-wrap: wrap; align-items: stretch;">
    <div style="flex: 1; min-width: 200px; background-color: #f0fdf4; border-radius: 8px; padding: 16px; border: 1px solid #bbf7d0; box-sizing: border-box; display: flex; flex-direction: column;">
      <div style="display: inline-block; background-color: #22c55e; color: #fff; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-bottom: 12px; align-self: flex-start;">正确</div>
      <div style="font-size: 14px; color: #166534; line-height: 1.6; flex: 1;">{left_content}</div>
    </div>
    <div style="flex: 1; min-width: 200px; background-color: #fef2f2; border-radius: 8px; padding: 16px; border: 1px solid #fecaca; box-sizing: border-box; display: flex; flex-direction: column;">
      <div style="display: inline-block; background-color: #ef4444; color: #fff; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-bottom: 12px; align-self: flex-start;">错误</div>
      <div style="font-size: 14px; color: #991b1b; line-height: 1.6; flex: 1;">{right_content}</div>
    </div>
  </div>
</section>'''

    def _render_focus(self, content: str, params: str, primary: str) -> str:
        """渲染 focus 组件：金句高亮"""
        bg_rgba = self._hex_to_rgba(primary, 0.1)
        text_color = self._get_contrast_color(primary)
        lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
        main_text = lines[0] if lines else content.strip()
        display_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', main_text)

        return f'''<section style="margin: 24px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="background-color: {bg_rgba}; border-top: 3px solid {primary}; border-bottom: 3px solid {primary}; border-radius: 0; padding: 32px 24px; text-align: center; position: relative;">
    <div style="font-size: 48px; color: {primary}40; position: absolute; top: 8px; left: 24px; font-family: Georgia, serif;">"</div>
    <div style="font-size: 20px; font-weight: bold; color: {text_color}; line-height: 1.6; position: relative; z-index: 1;">{display_text}</div>
    <div style="font-size: 48px; color: {primary}40; position: absolute; bottom: -16px; right: 24px; font-family: Georgia, serif;">"</div>
  </div>
</section>'''

    def parse(self, markdown: str, primary: str) -> str:
        """解析并替换 ::: 高级组件语法（逐行解析，避免与 --- 分隔符冲突）"""
        lines = markdown.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 检查是否是以 ::: 开头的组件开始
            # 匹配 ::: type 或 :::type
            match = re.match(r'^:::\s*(\w+)(.*)$', line)
            if match:
                container_type = match.group(1).strip()
                params = match.group(2).strip()

                # 收集组件内容，直到遇到单独的 ::: 行
                content_lines = []
                j = i + 1
                while j < len(lines):
                    if lines[j].strip() == ':::':
                        break
                    content_lines.append(lines[j])
                    j += 1

                content = '\n'.join(content_lines)

                # 渲染组件
                if container_type == 'release':
                    comp_html = self._render_release(content, params, primary)
                elif container_type == 'grid':
                    comp_html = self._render_grid(content, params, primary)
                elif container_type == 'timeline':
                    comp_html = self._render_timeline(content, params, primary)
                elif container_type == 'steps':
                    comp_html = self._render_steps(content, params, primary)
                elif container_type == 'compare':
                    comp_html = self._render_compare(content, params, primary)
                elif container_type == 'focus':
                    comp_html = self._render_focus(content, params, primary)
                else:
                    comp_html = f'<div style="margin:16px 0;padding:16px;border:1px dashed #ccc;">{content}</div>'

                result.append(comp_html)
                i = j + 1  # 跳过内容行和结束的 :::
            else:
                result.append(line)
                i += 1

        return '\n'.join(result)

        def replace_container(match):
            container_type = match.group(1).strip()
            params = match.group(2).strip()
            content = match.group(3).strip()

            if container_type == 'release':
                return self._render_release(content, params, primary)
            elif container_type == 'grid':
                return self._render_grid(content, params, primary)
            elif container_type == 'timeline':
                return self._render_timeline(content, params, primary)
            elif container_type == 'steps':
                return self._render_steps(content, params, primary)
            elif container_type == 'compare':
                return self._render_compare(content, params, primary)
            elif container_type == 'focus':
                return self._render_focus(content, params, primary)
            else:
                return f'<div style="margin:16px 0;padding:16px;border:1px dashed #ccc;">{content}</div>'

        return re.sub(pattern, replace_container, markdown)
