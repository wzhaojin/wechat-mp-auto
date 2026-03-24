"""
微信公众号自动化 - 参数验证工具
"""

import re
from pathlib import Path


class Validators:
    @staticmethod
    def validate_app_id(app_id: str) -> bool:
        return bool(re.match(r'^wx[a-zA-Z0-9]{16}$', app_id)) if app_id else False
    
    @staticmethod
    def validate_app_secret(secret: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9]{32}$', secret)) if secret else False
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))
    
    @staticmethod
    def validate_image_path(path: str) -> dict:
        file_path = Path(path)
        if not file_path.exists():
            return {"valid": False, "error": "文件不存在"}
        allowed = {".jpg", ".jpeg", ".png", ".gif"}
        if file_path.suffix.lower() not in allowed:
            return {"valid": False, "error": f"不支持格式"}
        return {"valid": True}
