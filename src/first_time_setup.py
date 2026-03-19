"""
微信公众号自动化 - 首次使用引导
"""

import json
from pathlib import Path
from typing import List, Dict


SETUP_GUIDE = """
📋 首次使用配置指南

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 获取 AppID 和 AppSecret
   网址: https://mp.weixin.qq.com/
   路径: 登录 → 开发 → 基本配置
   - AppID：应用ID
   - AppSecret：应用密钥（点击"启用"获取）

2️⃣ 设置 IP 白名单
   路径: 开发 → 基本配置 → IP白名单
   - 添加服务器公网 IP

3️⃣ 配置文件
   位置: ~/.config/wechat-mp-auto/config.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


class FirstTimeSetup:
    """首次使用引导"""
    
    CONFIG_DIR = Path.home() / ".config" / "wechat-mp-auto"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    @classmethod
    def check_and_prompt(cls) -> dict:
        """检查是否首次使用"""
        if not cls.CONFIG_FILE.exists():
            return {"is_first_time": True, "message": SETUP_GUIDE, "step": "credentials"}
        
        try:
            with open(cls.CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            return {"is_first_time": True, "message": SETUP_GUIDE, "step": "credentials"}
        
        if not config.get("app_id") or not config.get("app_secret"):
            return {"is_first_time": True, "message": SETUP_GUIDE, "step": "credentials"}
        
        if not config.get("default_template"):
            return {"is_first_time": True, "message": "请选择默认模板", "templates": cls._get_available_templates(), "step": "template"}
        
        return {"is_first_time": False, "message": "配置完成", "step": None}
    
    @classmethod
    def _get_available_templates(cls) -> List[dict]:
        templates = []
        themes_dir = Path(__file__).parent.parent.parent / "themes"
        if themes_dir.exists():
            for f in themes_dir.glob("*.yaml"):
                templates.append({"id": f.stem, "name": f.stem, "type": "local"})
        return templates if templates else [{"id": "default", "name": "默认主题", "type": "local"}]
    
    @classmethod
    def setup_credentials(cls, app_id: str, app_secret: str):
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {}
        if cls.CONFIG_FILE.exists():
            with open(cls.CONFIG_FILE) as f:
                config = json.load(f)
        config["app_id"] = app_id
        config["app_secret"] = app_secret
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def set_default_template(cls, template_type: str, template_id: str):
        config = {}
        if cls.CONFIG_FILE.exists():
            with open(cls.CONFIG_FILE) as f:
                config = json.load(f)
        config["default_template"] = {"type": template_type, "id": template_id}
        with open(cls.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def get_status(cls) -> dict:
        if not cls.CONFIG_FILE.exists():
            return {"status": "not_configured", "message": SETUP_GUIDE}
        try:
            with open(cls.CONFIG_FILE) as f:
                config = json.load(f)
        except Exception:
            return {"status": "error", "message": SETUP_GUIDE}
        
        has_cred = bool(config.get("app_id") and config.get("app_secret"))
        has_template = bool(config.get("default_template"))
        
        if not has_cred:
            return {"status": "need_credentials", "message": SETUP_GUIDE}
        elif not has_template:
            return {"status": "need_template", "message": "请选择默认模板"}
        else:
            return {"status": "ready", "message": "配置完成"}
