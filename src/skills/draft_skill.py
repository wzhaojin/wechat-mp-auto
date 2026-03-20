"""
微信公众号自动化 - 草稿箱管理 Skill
"""

import logging
from typing import List, Dict, Optional
from .base_skill import BaseSkill

# 配置日志
logger = logging.getLogger(__name__)


class DraftSkill(BaseSkill):
    """草稿箱管理"""

    def list_drafts(self, offset: int = 0, count: int = 20, no_content: bool = False) -> Dict:
        """获取草稿列表"""
        # 参数验证
        if not isinstance(offset, int) or offset < 0:
            logger.error(f"无效的offset: {offset}")
            raise ValueError("offset必须是大于等于0的整数")
        
        if not isinstance(count, int) or count < 1 or count > 20:
            logger.warning(f"无效的count: {count}, 使用默认值20")
            count = 20
        
        if not isinstance(no_content, bool):
            logger.warning(f"无效的no_content: {no_content}, 使用默认值False")
            no_content = False

        try:
            logger.info(f"获取草稿列表: offset={offset}, count={count}, no_content={no_content}")
            
            data = {"offset": offset, "count": count, "no_content": 1 if no_content else 0}
            result = self.post("/cgi-bin/draft/batchget", data)
            
            drafts = result.get("item", [])
            total_count = result.get("total_count", 0)
            
            logger.info(f"草稿列表获取成功: 总数={total_count}, 本次返回={len(drafts)}")
            
            return {"total_count": total_count, "drafts": drafts}
        except Exception as e:
            logger.error(f"获取草稿列表失败: {str(e)}", exc_info=True)
            raise

    def get_draft(self, media_id: str) -> Dict:
        """获取草稿详情"""
        # 参数验证
        if not media_id or not isinstance(media_id, str):
            logger.error("无效的media_id参数")
            raise ValueError("media_id不能为空且必须是字符串")
        
        if len(media_id) < 10:
            logger.error(f"media_id格式可能无效: {media_id}")
            raise ValueError("media_id格式无效")

        try:
            logger.info(f"获取草稿详情: media_id={media_id}")
            result = self.post("/cgi-bin/draft/get", {"media_id": media_id})
            logger.info(f"草稿详情获取成功: media_id={media_id}")
            return result
        except Exception as e:
            logger.error(f"获取草稿详情失败: {str(e)}", exc_info=True)
            raise

    def create_draft(self, articles: List[Dict], auto_upload_thumb: bool = False) -> Dict:
        """创建草稿
        
        Args:
            articles: 文章列表，每篇文章需包含 title, content 等字段
            auto_upload_thumb: 是否自动上传封面图。如果为True，会自动将文章HTML中
                             的第一张图片作为封面上传
        """
        # 参数验证
        if not articles or not isinstance(articles, list):
            logger.error("无效的articles参数: articles不能为空且必须是列表")
            raise ValueError("articles不能为空且必须是列表")
        
        if len(articles) > 8:
            logger.warning(f"文章数量过多({len(articles)}),微信限制最多8篇")
            articles = articles[:8]

        # 验证每篇文章的结构，并自动处理封面图
        for i, article in enumerate(articles):
            if not isinstance(article, dict):
                logger.error(f"无效的文章结构: 第{i+1}篇不是字典")
                raise ValueError(f"第{i+1}篇文章结构无效")
            
            # 至少需要title字段
            if "title" not in article or not article.get("title"):
                logger.warning(f"第{i+1}篇文章缺少标题")
            
            # 检查 thumb_media_id
            thumb_id = article.get("thumb_media_id", "")
            if not thumb_id and auto_upload_thumb:
                # 自动从HTML内容中提取第一张图片并上传作为封面
                content = article.get("content", "")
                if content:
                    import re
                    img_matches = re.findall(r'<img[^>]*src="([^"]+)"', content)
                    if img_matches:
                        first_img_url = img_matches[0]
                        logger.info(f"[{i+1}] 自动提取封面图: {first_img_url[:50]}...")
                        
                        # 下载并上传
                        try:
                            from .material_skill import MaterialSkill
                            mat = MaterialSkill()
                            
                            import requests
                            import uuid
                            from pathlib import Path
                            cache = Path.home() / ".cache" / "wechat-mp-auto" / "images"
                            cache.mkdir(parents=True, exist_ok=True)
                            
                            if first_img_url.startswith("http"):
                                resp = requests.get(first_img_url, timeout=30)
                                if resp.status_code == 200:
                                    local_file = cache / f"thumb_{uuid.uuid4().hex[:8]}.jpg"
                                    with open(local_file, "wb") as f:
                                        f.write(resp.content)
                                    
                                    upload_result = mat.upload_image(str(local_file))
                                    new_thumb_id = upload_result.get("media_id", "")
                                    if new_thumb_id:
                                        article["thumb_media_id"] = new_thumb_id
                                        logger.info(f"[{i+1}] 封面上传成功: {new_thumb_id[:20]}...")
                        except Exception as e:
                            logger.warning(f"[{i+1}] 自动封面上传失败: {e}")

        try:
            logger.info(f"创建草稿: articles_count={len(articles)}")
            result = self.post("/cgi-bin/draft/add", {"articles": articles})
            
            if "media_id" in result:
                logger.info(f"草稿创建成功: media_id={result['media_id']}")
            else:
                logger.warning(f"草稿创建返回结果异常: {result}")
            
            return result
        except Exception as e:
            logger.error(f"创建草稿失败: {str(e)}", exc_info=True)
            raise

    def update_draft(self, media_id: str, article: Dict, index: int = 0) -> Dict:
        """更新草稿"""
        # 参数验证
        if not media_id or not isinstance(media_id, str):
            logger.error("无效的media_id参数")
            raise ValueError("media_id不能为空且必须是字符串")
        
        if len(media_id) < 10:
            logger.error(f"media_id格式可能无效: {media_id}")
            raise ValueError("media_id格式无效")
        
        if not article or not isinstance(article, dict):
            logger.error("无效的article参数: article必须是字典")
            raise ValueError("article必须是字典")
        
        if not isinstance(index, int) or index < 0:
            logger.error(f"无效的index: {index}")
            raise ValueError("index必须是大于等于0的整数")

        try:
            logger.info(f"更新草稿: media_id={media_id}, index={index}")
            result = self.post("/cgi-bin/draft/update", {
                "media_id": media_id, 
                "index": index, 
                "articles": article
            })
            logger.info(f"草稿更新成功: media_id={media_id}")
            return result
        except Exception as e:
            logger.error(f"更新草稿失败: {str(e)}", exc_info=True)
            raise

    def delete_draft(self, media_id: str) -> Dict:
        """删除草稿"""
        # 参数验证
        if not media_id or not isinstance(media_id, str):
            logger.error("无效的media_id参数")
            raise ValueError("media_id不能为空且必须是字符串")
        
        if len(media_id) < 10:
            logger.error(f"media_id格式可能无效: {media_id}")
            raise ValueError("media_id格式无效")

        try:
            logger.info(f"删除草稿: media_id={media_id}")
            result = self.post("/cgi-bin/draft/delete", {"media_id": media_id})
            logger.info(f"草稿删除成功: media_id={media_id}")
            return result
        except Exception as e:
            logger.error(f"删除草稿失败: {str(e)}", exc_info=True)
            raise
