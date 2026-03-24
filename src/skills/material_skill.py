"""
微信公众号自动化 - 素材管理 Skill
"""

import os
import logging
import requests
from typing import List, Dict
from pathlib import Path
from .base_skill import BaseSkill

# 配置日志
logger = logging.getLogger(__name__)


class MaterialSkill(BaseSkill):
    """素材管理"""

    def upload_image(self, file_path: str) -> Dict:
        """上传图片素材"""
        # 参数验证
        if not file_path or not isinstance(file_path, str):
            logger.error("无效的file_path参数: file_path不能为空且必须是字符串")
            raise ValueError("file_path不能为空且必须是字符串")

        # 安全检查：验证文件路径
        if not os.path.isabs(file_path):
            logger.warning(f"建议使用绝对路径: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 安全检查：验证文件类型
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            logger.error(f"不支持的图片格式: {file_ext}")
            raise ValueError(f"不支持的图片格式: {file_ext}")

        # 安全检查：验证文件大小（微信限制20MB）
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 20 * 1024 * 1024:
                logger.error(f"文件过大: {file_size} bytes, 微信限制20MB")
                raise ValueError(f"文件过大: {file_size} bytes, 微信限制20MB")
        except OSError as e:
            logger.error(f"获取文件大小失败: {str(e)}")
            raise

        try:
            logger.info(f"开始上传图片素材: {file_path}")
            
            # 验证 access_token 存在
            if not hasattr(self, 'access_token') or not self.access_token:
                logger.error("access_token未设置")
                raise ValueError("access_token未设置，请先获取有效token")

            url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.access_token}&type=image"

            with open(file_path, "rb") as f:
                files = {"media": (os.path.basename(file_path), f, "image/jpeg")}
                response = requests.post(url, files=files, timeout=60).json()

            if "errcode" in response and response["errcode"] != 0:
                from exceptions import APIError
                error_msg = response.get("errmsg", "")
                logger.error(f"微信API错误: errcode={response['errcode']}, errmsg={error_msg}")
                raise APIError(response["errcode"], error_msg)

            logger.info(f"图片素材上传成功: media_id={response.get('media_id')}")
            
            return {
                "url": response.get("url"), 
                "media_id": response.get("media_id")
            }
        except FileNotFoundError:
            raise
        except ValueError:
            raise
        except ImportError as e:
            logger.error(f"缺少依赖库: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"上传图片素材失败: {str(e)}", exc_info=True)
            raise

    def upload_thumb(self, file_path: str) -> Dict:
        """上传封面图（缩略图）"""
        # 参数验证
        if not file_path or not isinstance(file_path, str):
            logger.error("无效的file_path参数")
            raise ValueError("file_path不能为空且必须是字符串")
        
        # 安全检查：封面图限制100KB
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                if file_size > 100 * 1024:
                    logger.warning(f"封面图可能过大: {file_size} bytes, 建议不超过100KB")
        except OSError:
            pass

        try:
            logger.info(f"开始上传封面图: {file_path}")
            return self.upload_image(file_path)
        except Exception as e:
            logger.error(f"上传封面图失败: {str(e)}", exc_info=True)
            raise

    def list_materials(self, material_type: str = "image", offset: int = 0, count: int = 20) -> Dict:
        """获取素材列表"""
        # 参数验证
        allowed_types = ["image", "voice", "video", "news"]
        if material_type not in allowed_types:
            logger.error(f"无效的material_type: {material_type}")
            raise ValueError(f"material_type必须是以下之一: {allowed_types}")
        
        if not isinstance(offset, int) or offset < 0:
            logger.error(f"无效的offset: {offset}")
            raise ValueError("offset必须是大于等于0的整数")
        
        if not isinstance(count, int) or count < 1 or count > 20:
            logger.warning(f"无效的count: {count}, 使用默认值20")
            count = 20

        try:
            logger.info(f"获取素材列表: type={material_type}, offset={offset}, count={count}")
            result = self.post("/cgi-bin/material/batchget_material", {
                "type": material_type, 
                "offset": offset, 
                "count": count
            })
            logger.info(f"素材列表获取成功: item_count={len(result.get('item', []))}")
            return result
        except Exception as e:
            logger.error(f"获取素材列表失败: {str(e)}", exc_info=True)
            raise

    def delete_material(self, media_id: str) -> Dict:
        """删除素材"""
        # 参数验证
        if not media_id or not isinstance(media_id, str):
            logger.error("无效的media_id参数")
            raise ValueError("media_id不能为空且必须是字符串")
        
        # 安全检查：media_id格式验证（微信media_id通常以特定前缀开头）
        if len(media_id) < 10:
            logger.error(f"media_id格式可能无效: {media_id}")
            raise ValueError("media_id格式无效")

        try:
            logger.info(f"删除素材: media_id={media_id}")
            result = self.post("/cgi-bin/material/delete", {"media_id": media_id})
            logger.info(f"素材删除成功: media_id={media_id}")
            return result
        except Exception as e:
            logger.error(f"删除素材失败: {str(e)}", exc_info=True)
            raise
