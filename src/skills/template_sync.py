"""
微信公众号自动化 - 模板同步 Skill

注意：微信公众平台的"文章模板"没有开放 API，无法下载/上传。
当前只支持本地模板管理。
"""

from typing import Dict
from .base_skill import BaseSkill


class TemplateSyncSkill(BaseSkill):
    """模板同步（本地 ↔ 微信）
    
    注意：微信文章模板没有开放 API，暂不支持下载/上传
    """
    
    def upload_to_wechat(self, template_name: str) -> Dict:
        """上传到微信（暂不支持）"""
        return {
            "success": False,
            "error": "微信文章模板没有开放 API，无法上传"
        }
    
    def download_from_wechat(self, media_id: str) -> Dict:
        """从微信下载（暂不支持）"""
        return {
            "success": False,
            "error": "微信文章模板没有开放 API，无法下载"
        }
    
    def sync_all(self, direction: str = "both") -> Dict:
        return {
            "success": False,
            "error": "微信文章模板没有开放 API"
        }
