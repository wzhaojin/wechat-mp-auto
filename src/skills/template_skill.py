"""
微信公众号自动化 - 模板管理 Skill
"""

import yaml
from pathlib import Path
from typing import List, Dict
from .base_skill import BaseSkill


class TemplateSkill(BaseSkill):
    """模板管理"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._themes_dir = Path(__file__).parent.parent.parent / "themes"
        self._themes_dir.mkdir(parents=True, exist_ok=True)
    
    def list_local_templates(self) -> List[Dict]:
        templates = []
        if self._themes_dir.exists():
            for yaml_file in self._themes_dir.glob("*.yaml"):
                with open(yaml_file) as f:
                    config = yaml.safe_load(f) or {}
                templates.append({"id": yaml_file.stem, "name": config.get("name", yaml_file.stem), "type": "local"})
        return templates if templates else [{"id": "default", "name": "默认主题", "type": "local"}]
    
    def list_wechat_templates(self) -> List[Dict]:
        result = self.get("/cgi-bin/template/get_all_private_template")
        return [{"id": t.get("template_id"), "title": t.get("title"), "type": "wechat"} for t in result.get("template_list", [])]
    
    def get_template_detail(self, template_id: str, template_type: str = "local") -> Dict:
        if template_type == "local":
            template_file = self._themes_dir / f"{template_id}.yaml"
            if template_file.exists():
                with open(template_file) as f:
                    config = yaml.safe_load(f)
            else:
                config = {"name": "默认", "colors": {"primary": "#007AFF"}}
            return {"id": template_id, "type": "local", "config": config}
        else:
            result = self.get("/cgi-bin/template/get_template", {"template_id": template_id})
            return {"id": template_id, "type": "wechat", "content": result.get("content", "")}
    
    def select_default_template(self) -> Dict:
        from ..config import Config
        config = Config()
        current = config.get_default_template()
        local = self.list_local_templates()
        wechat = self.list_wechat_templates()
        return {"current": current, "local_templates": local, "wechat_templates": wechat}
