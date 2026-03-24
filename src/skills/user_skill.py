"""
微信公众号自动化 - 用户管理 Skill
获取标签列表、粉丝列表、发送消息
"""

import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class UserSkill(BaseSkill):
    """用户管理 - 标签和粉丝管理"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user_cache_file = Path.home() / ".cache" / "wechat-mp-auto" / "user_cache.json"
        self._user_cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_user_cache(self) -> Dict:
        """加载用户缓存"""
        if not self._user_cache_file.exists():
            return {"users": {}, "tags": {}}
        try:
            with open(self._user_cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载用户缓存失败: {e}")
            return {"users": {}, "tags": {}}
    
    def _save_user_cache(self, cache: Dict):
        """保存用户缓存"""
        try:
            with open(self._user_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存用户缓存失败: {e}")
    
    def add_user(self, openid: str, user_info: Dict) -> bool:
        """添加或更新用户信息
        
        Args:
            openid: 用户openid
            user_info: 用户信息 {nickname, remark, tagid_list, etc.}
        
        Returns:
            是否成功
        """
        try:
            cache = self._load_user_cache()
            cache["users"][openid] = {
                **user_info,
                "added_at": self._get_timestamp()
            }
            self._save_user_cache(cache)
            logger.info(f"添加用户成功: {openid}")
            return True
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
    
    def get_user(self, openid: str) -> Optional[Dict]:
        """获取用户信息"""
        cache = self._load_user_cache()
        return cache.get("users", {}).get(openid)
    
    def list_users(self) -> List[Dict]:
        """列出所有已缓存的用户"""
        cache = self._load_user_cache()
        return list(cache.get("users", {}).values())
    
    def get_tags(self) -> List[Dict]:
        """获取公众号标签列表
        
        Returns:
            [{"id": 1, "name": "标签名"}, ...]
        """
        try:
            result = self._request("GET", "/cgi-bin/tags/get", params={})
            tags = result.get("tags", [])
            logger.info(f"获取标签列表成功: {len(tags)} 个标签")
            
            # 缓存标签信息
            cache = self._load_user_cache()
            cache["tags"] = {str(t.get("id")): t for t in tags}
            self._save_user_cache(cache)
            
            return tags
        except Exception as e:
            logger.error(f"获取标签列表失败: {e}")
            raise
    
    def get_tag_fans(self, tag_id: int, next_openid: str = "") -> Dict:
        """获取指定标签下的粉丝列表
        
        Args:
            tag_id: 标签ID
            next_openid: 第一个拉取的openid，不填默认从头开始
        
        Returns:
            {
                "count": 粉丝数量,
                "data": {"openid": [openid列表]},
                "next_openid": 下次拉取的起始openid
            }
        """
        try:
            result = self._request(
                "GET", 
                "/cgi-bin/user/tag/get",
                params={
                    "tagid": tag_id,
                    "next_openid": next_openid
                }
            )
            
            count = result.get("count", 0)
            data = result.get("data", {})
            openids = data.get("openid", [])
            
            logger.info(f"获取标签 {tag_id} 粉丝成功: {count} 人")
            
            return {
                "count": count,
                "data": data,
                "next_openid": result.get("next_openid", ""),
                "tag_id": tag_id
            }
        except Exception as e:
            logger.error(f"获取标签粉丝列表失败: {e}")
            raise
    
    def get_all_tag_fans(self, tag_id: int) -> List[str]:
        """获取指定标签下的所有粉丝openid
        
        Args:
            tag_id: 标签ID
        
        Returns:
            openid列表
        """
        all_openids = []
        next_openid = ""
        
        try:
            while True:
                result = self.get_tag_fans(tag_id, next_openid)
                openids = result.get("data", {}).get("openid", [])
                all_openids.extend(openids)
                
                next_openid = result.get("next_openid", "")
                if not next_openid or next_openid == "0":
                    break
            
            logger.info(f"获取全部粉丝完成: 共 {len(all_openids)} 人")
            return all_openids
        except Exception as e:
            logger.error(f"获取全部粉丝失败: {e}")
            return all_openids
    
    def get_user_info(self, openid: str, lang: str = "zh_CN") -> Optional[Dict]:
        """获取用户基本信息
        
        Args:
            openid: 用户openid
            lang: 返回语言版本，zh_CN 简体，zh_TW 繁体，en 英语
        
        Returns:
            用户信息字典
        """
        try:
            result = self._request(
                "GET",
                "/cgi-bin/user/info",
                params={
                    "openid": openid,
                    "lang": lang
                }
            )
            
            # 缓存用户信息
            self.add_user(openid, result)
            
            logger.info(f"获取用户信息成功: {openid}")
            return result
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    def batch_get_user_info(self, openids: List[str], lang: str = "zh_CN") -> List[Dict]:
        """批量获取用户基本信息
        
        Args:
            openids: openid列表（最多100个）
            lang: 返回语言版本
        
        Returns:
            用户信息列表
        """
        if not openids:
            return []
        
        # 每次最多100个
        results = []
        for i in range(0, len(openids), 100):
            batch = openids[i:i+100]
            try:
                result = self._request(
                    "POST",
                    "/cgi-bin/user/info/batchget",
                    data={
                        "user_list": [{"openid": oid, "lang": lang} for oid in batch]
                    }
                )
                user_list = result.get("user_info_list", [])
                results.extend(user_list)
                
                # 缓存用户信息
                for user in user_list:
                    oid = user.get("openid")
                    if oid:
                        self.add_user(oid, user)
                
                logger.info(f"批量获取用户信息: {len(batch)} 人")
            except Exception as e:
                logger.error(f"批量获取用户信息失败: {e}")
                continue
        
        return results
    
    def get_fans_summary(self, tag_id: Optional[int] = None) -> Dict:
        """获取粉丝摘要信息
        
        Args:
            tag_id: 标签ID，如果为None则获取全部粉丝
        
        Returns:
            {
                "total": 总粉丝数,
                "tags": {tag_id: count},
                "users": 用户列表
            }
        """
        summary = {
            "total": 0,
            "tags": {},
            "users": []
        }
        
        try:
            # 如果指定了标签
            if tag_id:
                openids = self.get_all_tag_fans(tag_id)
                summary["total"] = len(openids)
                summary["tags"][str(tag_id)] = len(openids)
                
                # 批量获取用户信息
                users = self.batch_get_user_info(openids[:50])  # 最多获取50人详细信息
                summary["users"] = users
            else:
                # 获取所有标签
                tags = self.get_tags()
                
                for tag in tags:
                    tid = tag.get("id")
                    tname = tag.get("name", "")
                    count = tag.get("count", 0)
                    
                    summary["tags"][str(tid)] = {
                        "name": tname,
                        "count": count
                    }
                    summary["total"] += count
                
                # 获取第一个标签的粉丝作为示例
                if tags:
                    first_tag = tags[0]
                    tid = first_tag.get("id")
                    openids = self.get_all_tag_fans(tid)
                    users = self.batch_get_user_info(openids[:20])
                    summary["users"] = users
            
            return summary
        except Exception as e:
            logger.error(f"获取粉丝摘要失败: {e}")
            return summary
    
    def _get_timestamp(self) -> int:
        """获取当前时间戳"""
        import time
        return int(time.time())
    
    def clear_user_cache(self) -> bool:
        """清除用户缓存"""
        try:
            if self._user_cache_file.exists():
                self._user_cache_file.unlink()
            logger.info("用户缓存已清除")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False
