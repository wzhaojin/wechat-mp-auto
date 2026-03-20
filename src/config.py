"""
微信公众号自动化 - 配置管理
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict

# 配置日志
logger = logging.getLogger(__name__)


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG_DIR = Path.home() / ".config" / "wechat-mp-auto"
    DEFAULT_CACHE_DIR = Path.home() / ".cache" / "wechat-mp-auto"
    
    def __init__(self):
        self._config = {}
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        try:
            self.DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"配置目录已创建/确认: {self.DEFAULT_CONFIG_DIR}")
        except PermissionError as e:
            logger.error(f"创建配置目录权限不足: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"创建配置目录失败: {str(e)}")
            raise
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取凭证 - 优先级：配置文件 > 环境变量 > .env
        """
        app_id = None
        app_secret = None
        
        # 1. 优先从配置文件读取
        config_file = self.DEFAULT_CONFIG_DIR / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    app_id = data.get("app_id")
                    app_secret = data.get("app_secret")
                    if app_id and app_secret:
                        logger.info("从配置文件读取凭证成功")
                        return app_id, app_secret
            except json.JSONDecodeError as e:
                logger.error(f"配置文件JSON解析失败: {str(e)}")
            except PermissionError as e:
                logger.error(f"读取配置文件权限不足: {str(e)}")
            except Exception as e:
                logger.error(f"读取配置文件失败: {str(e)}")
        
        # 2. 从环境变量读取
        app_id = os.environ.get("WECHAT_APP_ID")
        app_secret = os.environ.get("WECHAT_APP_SECRET")
        if app_id and app_secret:
            logger.info("从环境变量读取凭证成功")
            return app_id, app_secret
        
        # 3. 从 .env 读取
        env_file = Path.home() / ".openclaw" / ".env"
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" in line:
                                key, value = line.split("=", 1)
                                if key == "WECHAT_APP_ID":
                                    app_id = value.strip()
                                elif key == "WECHAT_APP_SECRET":
                                    app_secret = value.strip()
                
                if app_id and app_secret:
                    logger.info("从.env文件读取凭证成功")
                    return app_id, app_secret
            except PermissionError as e:
                logger.error(f"读取.env文件权限不足: {str(e)}")
            except Exception as e:
                logger.error(f"读取.env文件失败: {str(e)}")
        
        logger.error("未配置微信公众号凭证")
        raise Exception("未配置微信公众号凭证")
    
    def get_default_template(self) -> dict:
        """获取默认模板"""
        config_file = self.DEFAULT_CONFIG_DIR / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = data.get("default_template", {"type": "local", "id": "default"})
                    logger.debug(f"获取默认模板: {template}")
                    return template
            except json.JSONDecodeError as e:
                logger.error(f"配置文件JSON解析失败: {str(e)}")
            except PermissionError as e:
                logger.error(f"读取配置文件权限不足: {str(e)}")
            except Exception as e:
                logger.error(f"读取配置文件失败: {str(e)}")
        
        default_template = {"type": "local", "id": "default"}
        logger.debug(f"使用默认模板: {default_template}")
        return default_template
    
    def set_default_template(self, template_type: str, template_id: str):
        """设置默认模板"""
        # 参数验证
        if not template_type or not isinstance(template_type, str):
            logger.error("无效的template_type参数")
            raise ValueError("template_type不能为空且必须是字符串")
        
        if not template_id or not isinstance(template_id, str):
            logger.error("无效的template_id参数")
            raise ValueError("template_id不能为空且必须是字符串")

        try:
            config_file = self.DEFAULT_CONFIG_DIR / "config.json"
            config = {}
            
            # 读取现有配置
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("配置文件JSON解析失败，将创建新配置")
                except Exception as e:
                    logger.warning(f"读取配置文件失败: {str(e)}")
            
            # 更新模板配置
            config["default_template"] = {"type": template_type, "id": template_id}
            
            # 写入配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"默认模板设置成功: type={template_type}, id={template_id}")
        except PermissionError as e:
            logger.error(f"写入配置文件权限不足: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"设置默认模板失败: {str(e)}")
            raise

    # ========== 图片来源和模型偏好 ==========

    def get_image_preferences(self) -> Dict:
        """获取图片来源和模型偏好配置"""
        config_file = self.DEFAULT_CONFIG_DIR / "config.json"
        defaults = {
            "image_source": None,   # "ai" 或 "search"
            "ai_model": None,        # 模型 ID 如 "glm-5", "dall-e-3", "kimi" 等
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    defaults["image_source"] = data.get("image_source")
                    defaults["ai_model"] = data.get("ai_model")
            except Exception as e:
                logger.warning(f"读取图片偏好失败: {str(e)}")
        
        return defaults

    def set_image_source_preference(self, source: str):
        """设置图片来源偏好"""
        if source not in ("ai", "search"):
            raise ValueError("图片来源只支持 'ai' 或 'search'")
        
        config_file = self.DEFAULT_CONFIG_DIR / "config.json"
        config = {}
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                pass
        
        config["image_source"] = source
        
        # 更换图片来源时，清空模型偏好（需重新选择）
        if source == "search":
            config.pop("ai_model", None)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"图片来源偏好已保存: {source}")

    def set_ai_model_preference(self, model_id: str):
        """设置AI生图模型偏好"""
        if not model_id:
            raise ValueError("模型ID不能为空")
        
        config_file = self.DEFAULT_CONFIG_DIR / "config.json"
        config = {}
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception:
                pass
        
        config["image_source"] = "ai"
        config["ai_model"] = model_id
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"AI模型偏好已保存: {model_id}")


# 全局配置实例
config = Config()
