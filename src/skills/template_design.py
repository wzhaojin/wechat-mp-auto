"""
微信公众号自动化 - 模板设计 Skill
"""

import yaml
from pathlib import Path
from typing import Dict
from .base_skill import BaseSkill


class TemplateDesignSkill(BaseSkill):
    """模板设计制作"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._themes_dir = Path(__file__).parent.parent.parent / "themes"
        self._themes_dir.mkdir(parents=True, exist_ok=True)
    
    def create_template(self, config: Dict) -> Dict:
        theme_name = config.get("theme_name", "custom")
        
        template_config = {
            "name": config.get("theme_name", "自定义主题"),
            "colors": {
                "primary": config.get("primary_color", "#007AFF"),
                "secondary": config.get("secondary_color", "#5856D6"),
                "text": config.get("text_color", "#333333")
            },
            "body": {
                "font_size": "15px",
                "line_height": "1.8"
            }
        }
        
        output_file = self._themes_dir / f"{theme_name}.yaml"
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(template_config, f, allow_unicode=True, default_flow_style=False)
        
        return {"success": True, "template_id": theme_name, "path": str(output_file)}
    
    def validate_template(self, template_path: str) -> Dict:
        try:
            with open(template_path) as f:
                yaml.safe_load(f)
            return {"valid": True, "issues": []}
        except Exception as e:
            return {"valid": False, "issues": [str(e)]}
