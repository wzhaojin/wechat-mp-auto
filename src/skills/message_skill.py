"""
微信公众号自动化 - 消息发送 Skill
向用户发送图文消息
"""

import json
import logging
from typing import List, Dict, Optional, Any
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class MessageSkill(BaseSkill):
    """消息发送 - 向用户发送文章"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def send_text(self, openid: str, content: str) -> Dict:
        """发送文本消息
        
        Args:
            openid: 用户openid
            content: 文本内容
        
        Returns:
            {"errcode": 0, "errmsg": "ok"}
        """
        try:
            result = self._request(
                "POST",
                "/cgi-bin/message/custom/send",
                data={
                    "touser": openid,
                    "msgtype": "text",
                    "text": {"content": content}
                }
            )
            
            if result.get("errcode") == 0:
                logger.info(f"发送文本消息成功: {openid}")
            else:
                logger.error(f"发送文本消息失败: {result.get('errmsg')}")
            
            return result
        except Exception as e:
            logger.error(f"发送文本消息异常: {e}")
            raise
    
    def send_article(self, openid: str, media_id: str) -> Dict:
        """发送图文消息（需要先上传到素材库）
        
        Args:
            openid: 用户openid
            media_id: 图文消息的media_id（通过草稿箱转素材获取）
        
        Returns:
            {"errcode": 0, "errmsg": "ok"}
        """
        try:
            result = self._request(
                "POST",
                "/cgi-bin/message/custom/send",
                data={
                    "touser": openid,
                    "msgtype": "mpnews",
                    "mpnews": {"media_id": media_id}
                }
            )
            
            if result.get("errcode") == 0:
                logger.info(f"发送图文消息成功: {openid}, media_id: {media_id}")
            else:
                logger.error(f"发送图文消息失败: {result.get('errmsg')}")
            
            return result
        except Exception as e:
            logger.error(f"发送图文消息异常: {e}")
            raise
    
    def send_article_link(self, openid: str, title: str, content: str, 
                        url: str, thumb_url: str) -> Dict:
        """发送文章链接消息
        
        Args:
            openid: 用户openid
            title: 文章标题
            content: 文章摘要
            url: 文章链接
            thumb_url: 封面图片链接
        
        Returns:
            {"errcode": 0, "errmsg": "ok"}
        """
        try:
            result = self._request(
                "POST",
                "/cgi-bin/message/custom/send",
                data={
                    "touser": openid,
                    "msgtype": "link",
                    "link": {
                        "title": title,
                        "description": content,
                        "url": url,
                        "thumb_url": thumb_url
                    }
                }
            )
            
            if result.get("errcode") == 0:
                logger.info(f"发送链接消息成功: {openid}")
            else:
                logger.error(f"发送链接消息失败: {result.get('errmsg')}")
            
            return result
        except Exception as e:
            logger.error(f"发送链接消息异常: {e}")
            raise
    
    def send_to_multiple(self, openids: List[str], message_func, *args, **kwargs) -> Dict:
        """群发消息
        
        Args:
            openids: openid列表
            message_func: 发送函数（如 self.send_text）
            *args, **kwargs: 传递给发送函数的参数
        
        Returns:
            {
                "success": 成功数,
                "failed": 失败数,
                "results": [每个openid的发送结果]
            }
        """
        results = {
            "success": 0,
            "failed": 0,
            "results": []
        }
        
        for openid in openids:
            try:
                result = message_func(openid, *args, **kwargs)
                if result.get("errcode") == 0:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["results"].append({
                        "openid": openid,
                        "error": result.get("errmsg")
                    })
            except Exception as e:
                results["failed"] += 1
                results["results"].append({
                    "openid": openid,
                    "error": str(e)
                })
        
        logger.info(f"群发完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results
    
    def broadcast_article(self, openids: List[str], article_info: Dict) -> Dict:
        """群发文章
        
        Args:
            openids: openid列表
            article_info: 文章信息 {
                "type": "text" | "link" | "mpnews",
                "media_id": 图文media_id (mpnews用),
                "title": 标题 (link用),
                "content": 内容 (text/link用),
                "url": 链接 (link用),
                "thumb_url": 封面图 (link用)
            }
        
        Returns:
            群发结果
        """
        msg_type = article_info.get("type", "text")
        
        if msg_type == "text":
            return self.send_to_multiple(
                openids, 
                self.send_text,
                article_info.get("content", "")
            )
        elif msg_type == "link":
            return self.send_to_multiple(
                openids,
                self.send_article_link,
                article_info.get("title", ""),
                article_info.get("content", ""),
                article_info.get("url", ""),
                article_info.get("thumb_url", "")
            )
        elif msg_type == "mpnews":
            return self.send_to_multiple(
                openids,
                self.send_article,
                article_info.get("media_id", "")
            )
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")
    
    def preview_article(self, openid: str, article_info: Dict) -> Dict:
        """预览文章（发送给指定用户测试）
        
        Args:
            openid: 预览用户openid
            article_info: 文章信息（同broadcast_article）
        
        Returns:
            发送结果
        """
        msg_type = article_info.get("type", "text")
        
        if msg_type == "text":
            return self.send_text(openid, article_info.get("content", ""))
        elif msg_type == "link":
            return self.send_article_link(
                openid,
                article_info.get("title", ""),
                article_info.get("content", ""),
                article_info.get("url", ""),
                article_info.get("thumb_url", "")
            )
        elif msg_type == "mpnews":
            return self.send_article(openid, article_info.get("media_id", ""))
        else:
            raise ValueError(f"不支持的消息类型: {msg_type}")
