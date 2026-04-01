"""
微信公众号自动化 - 评论管理 Skill
支持打开/关闭留言、查看留言、标记精选、回复等操作

从 wechat-allauto-gzh 项目借鉴
"""

import logging
from typing import Dict, Optional, List
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class CommentSkill(BaseSkill):
    """评论/留言管理"""

    def open_comment(self, msg_data_id: int, index: int = 0) -> Dict:
        """
        打开已群发文章留言功能
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇，从0开始
        
        Returns:
            API响应结果
        """
        if not isinstance(msg_data_id, int) or msg_data_id <= 0:
            raise ValueError("msg_data_id 必须是正整数")
        
        try:
            logger.info(f"打开留言: msg_data_id={msg_data_id}, index={index}")
            result = self.post("/cgi-bin/comment/open", {
                "msg_data_id": msg_data_id,
                "index": index
            })
            logger.info(f"留言已打开: {result}")
            return result
        except Exception as e:
            logger.error(f"打开留言失败: {e}")
            raise

    def close_comment(self, msg_data_id: int, index: int = 0) -> Dict:
        """
        关闭已群发文章留言功能
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇，从0开始
        """
        if not isinstance(msg_data_id, int) or msg_data_id <= 0:
            raise ValueError("msg_data_id 必须是正整数")
        
        try:
            logger.info(f"关闭留言: msg_data_id={msg_data_id}, index={index}")
            result = self.post("/cgi-bin/comment/close", {
                "msg_data_id": msg_data_id,
                "index": index
            })
            logger.info(f"留言已关闭: {result}")
            return result
        except Exception as e:
            logger.error(f"关闭留言失败: {e}")
            raise

    def get_comment_list(
        self,
        msg_data_id: int,
        index: int = 0,
        begin: int = 0,
        count: int = 50,
        comment_type: int = 0
    ) -> Dict:
        """
        查看指定文章的留言数据
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇，从0开始
            begin: 起始位置
            count: 获取数量，最大200
            comment_type: 0-普通留言，1-精选留言
        """
        if not isinstance(msg_data_id, int) or msg_data_id <= 0:
            raise ValueError("msg_data_id 必须是正整数")
        
        if not 0 <= comment_type <= 1:
            raise ValueError("comment_type 必须是 0（普通）或 1（精选）")
        
        try:
            logger.info(f"获取留言列表: msg_data_id={msg_data_id}, type={comment_type}")
            result = self.post("/cgi-bin/comment/list", {
                "msg_data_id": msg_data_id,
                "index": index,
                "begin": begin,
                "count": min(count, 200),
                "type": comment_type
            })
            
            comments = result.get("comment", [])
            logger.info(f"获取到 {len(comments)} 条留言")
            return result
        except Exception as e:
            logger.error(f"获取留言列表失败: {e}")
            raise

    def mark_elect_comment(
        self,
        msg_data_id: int,
        index: int,
        user_comment_id: int
    ) -> Dict:
        """
        将留言标记为精选
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇
            user_comment_id: 用户留言的 comment_id
        """
        try:
            logger.info(f"标记精选留言: comment_id={user_comment_id}")
            result = self.post("/cgi-bin/comment/markelect", {
                "msg_data_id": msg_data_id,
                "index": index,
                "user_comment_id": user_comment_id
            })
            logger.info(f"精选标记成功: {result}")
            return result
        except Exception as e:
            logger.error(f"标记精选失败: {e}")
            raise

    def unmark_elect_comment(
        self,
        msg_data_id: int,
        index: int,
        user_comment_id: int
    ) -> Dict:
        """
        取消留言精选
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇
            user_comment_id: 用户留言的 comment_id
        """
        try:
            logger.info(f"取消精选留言: comment_id={user_comment_id}")
            result = self.post("/cgi-bin/comment/unmarkelect", {
                "msg_data_id": msg_data_id,
                "index": index,
                "user_comment_id": user_comment_id
            })
            logger.info(f"取消精选成功: {result}")
            return result
        except Exception as e:
            logger.error(f"取消精选失败: {e}")
            raise

    def delete_comment(
        self,
        msg_data_id: int,
        index: int,
        user_comment_id: int
    ) -> Dict:
        """
        删除留言
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇
            user_comment_id: 用户留言的 comment_id
        """
        try:
            logger.info(f"删除留言: comment_id={user_comment_id}")
            result = self.post("/cgi-bin/comment/delete", {
                "msg_data_id": msg_data_id,
                "index": index,
                "user_comment_id": user_comment_id
            })
            logger.info(f"留言删除成功: {result}")
            return result
        except Exception as e:
            logger.error(f"删除留言失败: {e}")
            raise

    def reply_comment(
        self,
        msg_data_id: int,
        index: int,
        user_comment_id: int,
        content: str
    ) -> Dict:
        """
        回复留言
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇
            user_comment_id: 用户留言的 comment_id
            content: 回复内容，最多300字符
        """
        if not content or len(content) > 300:
            raise ValueError("回复内容不能为空且最多300字符")
        
        try:
            logger.info(f"回复留言: comment_id={user_comment_id}")
            result = self.post("/cgi-bin/comment/reply/add", {
                "msg_data_id": msg_data_id,
                "index": index,
                "user_comment_id": user_comment_id,
                "content": content
            })
            logger.info(f"回复成功: {result}")
            return result
        except Exception as e:
            logger.error(f"回复留言失败: {e}")
            raise

    def delete_reply(
        self,
        msg_data_id: int,
        index: int,
        user_comment_id: int
    ) -> Dict:
        """
        删除回复（删除已发表的回复）
        
        Args:
            msg_data_id: 群发消息返回的 msg_data_id
            index: 多图文时第几篇
            user_comment_id: 用户留言的 comment_id
        """
        try:
            logger.info(f"删除回复: comment_id={user_comment_id}")
            result = self.post("/cgi-bin/comment/reply/delete", {
                "msg_data_id": msg_data_id,
                "index": index,
                "user_comment_id": user_comment_id
            })
            logger.info(f"回复删除成功: {result}")
            return result
        except Exception as e:
            logger.error(f"删除回复失败: {e}")
            raise
