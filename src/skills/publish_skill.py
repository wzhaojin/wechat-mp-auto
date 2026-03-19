"""
微信公众号自动化 - 发布管理 Skill
"""

import logging
from typing import List, Dict, Optional
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class PublishSkill(BaseSkill):
    """发布管理"""
    
    def publish_draft(self, media_id: str) -> Dict:
        """发布草稿到公众号"""
        # 参数验证
        if not media_id or not isinstance(media_id, str):
            logger.error("无效的media_id参数")
            raise ValueError("media_id不能为空且必须是字符串")
        
        if len(media_id) < 10:
            logger.error(f"media_id格式可能无效: {media_id}")
            raise ValueError("media_id格式无效")
        
        try:
            logger.info(f"发布草稿: media_id={media_id[:20]}...")
            result = self.post("/cgi-bin/freepublish/submit", {"media_id": media_id})
            logger.info(f"草稿发布成功: {media_id[:20]}...")
            return result
        except Exception as e:
            logger.error(f"发布草稿失败: {str(e)}", exc_info=True)
            raise
    
    def get_publish_status(self, publish_id: str) -> Dict:
        """获取发布状态"""
        # 参数验证
        if not publish_id or not isinstance(publish_id, str):
            logger.error("无效的publish_id参数")
            raise ValueError("publish_id不能为空且必须是字符串")
        
        try:
            logger.info(f"查询发布状态: publish_id={publish_id[:20]}...")
            result = self.get("/cgi-bin/freepublish/get", {"publish_id": publish_id})
            return result
        except Exception as e:
            logger.error(f"查询发布状态失败: {str(e)}", exc_info=True)
            raise
    
    def delete_published(self, article_id: str) -> Dict:
        """删除已发布文章"""
        # 参数验证
        if not article_id or not isinstance(article_id, str):
            logger.error("无效的article_id参数")
            raise ValueError("article_id不能为空且必须是字符串")
        
        try:
            logger.info(f"删除已发布文章: article_id={article_id[:20]}...")
            result = self.post("/cgi-bin/freepublish/delete", {"article_id": article_id})
            logger.info(f"文章删除成功: {article_id[:20]}...")
            return result
        except Exception as e:
            logger.error(f"删除文章失败: {str(e)}", exc_info=True)
            raise
    
    def list_published(self, offset: int = 0, count: int = 20) -> Dict:
        """获取已发布文章列表"""
        # 参数验证
        if not isinstance(offset, int) or offset < 0:
            logger.warning(f"无效的offset: {offset}, 使用默认值0")
            offset = 0
        
        if not isinstance(count, int) or count < 1 or count > 20:
            logger.warning(f"无效的count: {count}, 使用默认值20")
            count = 20
        
        try:
            logger.info(f"获取已发布列表: offset={offset}, count={count}")
            result = self.get("/cgi-bin/freepublish/batchget", {"offset": offset, "count": count})
            total = result.get("total_count", 0)
            logger.info(f"已发布文章总数: {total}")
            return result
        except Exception as e:
            logger.error(f"获取已发布列表失败: {str(e)}", exc_info=True)
            raise
    
    def batch_publish(self, media_ids: List[str]) -> Dict:
        """批量发布草稿"""
        # 参数验证
        if not media_ids or not isinstance(media_ids, list):
            logger.error("无效的media_ids参数")
            raise ValueError("media_ids不能为空且必须是列表")
        
        if len(media_ids) > 10:
            logger.warning(f"批量发布数量过多({len(media_ids)}),限制为10个")
            media_ids = media_ids[:10]
        
        results = []
        errors = []
        
        for media_id in media_ids:
            try:
                result = self.publish_draft(media_id)
                results.append({
                    "media_id": media_id,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                errors.append({
                    "media_id": media_id,
                    "success": False,
                    "error": str(e)
                })
                logger.warning(f"发布失败: {media_id[:20]}... - {str(e)}")
        
        return {
            "total": len(media_ids),
            "success": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
