"""
微信公众号自动化 - Token 管理器
"""

import time
import json
import logging
from pathlib import Path
from typing import Optional

# 配置日志
logger = logging.getLogger(__name__)


class TokenManager:
    """Access Token 管理器"""
    
    TOKEN_CACHE_FILE = Path.home() / ".cache" / "wechat-mp-auto" / "token.json"
    
    def __init__(self, app_id: str, app_secret: str):
        # 参数验证
        if not app_id or not isinstance(app_id, str):
            logger.error("无效的app_id参数")
            raise ValueError("app_id不能为空且必须是字符串")
        
        if not app_secret or not isinstance(app_secret, str):
            logger.error("无效的app_secret参数")
            raise ValueError("app_secret不能为空且必须是字符串")
        
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._expires_at: int = 0
        
        # 安全检查：确保app_id格式合理（微信app_id通常有特定格式）
        if len(app_id) < 10:
            logger.warning(f"app_id长度可能不正确: {app_id}")
        
        if len(app_secret) < 10:
            logger.warning(f"app_secret长度可能不正确")
        
        self._load_from_cache()
        logger.info(f"TokenManager初始化完成: app_id={app_id[:10]}...")
    
    def _load_from_cache(self):
        """从文件缓存加载"""
        if not self.TOKEN_CACHE_FILE.exists():
            logger.debug("Token缓存文件不存在")
            return
        
        try:
            with open(self.TOKEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 安全验证：检查app_id匹配
                if data.get("app_id") != self.app_id:
                    logger.warning("缓存的app_id与当前不匹配，清除缓存")
                    return
                
                self._access_token = data.get("access_token")
                self._expires_at = data.get("expires_at", 0)
                
                if self._access_token and not self._is_expired():
                    logger.debug("从缓存加载有效token")
                else:
                    logger.debug("缓存token已过期或无效")
        except json.JSONDecodeError as e:
            logger.warning(f"Token缓存文件JSON解析失败: {str(e)}")
        except PermissionError as e:
            logger.warning(f"读取Token缓存文件权限不足: {str(e)}")
        except Exception as e:
            logger.warning(f"加载Token缓存失败: {str(e)}")
    
    def _save_to_cache(self):
        """保存到文件"""
        try:
            # 安全检查：确保目录存在且路径安全
            self.TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # 安全检查：确保文件路径安全（在预期目录内）
            resolved_path = self.TOKEN_CACHE_FILE.resolve()
            expected_dir = (Path.home() / ".cache" / "wechat-mp-auto").resolve()
            if not str(resolved_path).startswith(str(expected_dir)):
                logger.error("不安全的缓存文件路径")
                return
            
            data = {
                "app_id": self.app_id,
                "access_token": self._access_token,
                "expires_at": self._expires_at
            }
            
            with open(self.TOKEN_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            
            logger.debug("Token已保存到缓存")
        except PermissionError as e:
            logger.error(f"写入Token缓存文件权限不足: {str(e)}")
        except Exception as e:
            logger.error(f"保存Token缓存失败: {str(e)}")
    
    def _is_expired(self) -> bool:
        """检查token是否过期（提前5分钟认为过期）"""
        # 安全检查：确保时间戳有效
        if self._expires_at <= 0:
            return True
        
        is_expired = time.time() >= (self._expires_at - 300)
        if is_expired:
            logger.debug("Token已过期")
        return is_expired
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token"""
        # 参数验证
        if not isinstance(force_refresh, bool):
            logger.warning(f"无效的force_refresh参数: {force_refresh}, 使用默认值False")
            force_refresh = False

        try:
            if force_refresh:
                logger.info("强制刷新Token")
                self._access_token = None
            
            # 检查现有token是否有效
            if self._access_token and not self._is_expired():
                logger.debug("使用缓存的有效Token")
                return self._access_token
            
            # 请求新的token
            logger.info("请求新的Access Token")
            
            try:
                import requests
            except ImportError:
                logger.error("requests库未安装")
                raise Exception("缺少requests库")
            
            # 安全：URL参数不记录敏感信息
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret=***"
            
            response = requests.get(
                f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}",
                timeout=10
            ).json()
            
            if "access_token" not in response:
                from .exceptions import APIError, get_error_message
                errcode = response.get("errcode", -1)
                errmsg = response.get("errmsg", get_error_message(errcode))
                logger.error(f"获取Token失败: errcode={errcode}, errmsg={errmsg}")
                raise APIError(errcode, errmsg)
            
            self._access_token = response["access_token"]
            self._expires_at = int(time.time()) + response.get("expires_in", 7200)
            self._save_to_cache()
            
            logger.info(f"Access Token获取成功，有效期至: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._expires_at))}")
            
            return self._access_token
        except ImportError:
            raise
        except Exception as e:
            logger.error(f"获取Access Token失败: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def from_config(cls, config) -> "TokenManager":
        """从配置创建"""
        # 参数验证
        if config is None:
            logger.error("config参数不能为空")
            raise ValueError("config不能为空")
        
        try:
            app_id, app_secret = config.get_credentials()
            logger.info("从配置创建TokenManager")
            return cls(app_id, app_secret)
        except Exception as e:
            logger.error(f"从配置创建TokenManager失败: {str(e)}")
            raise
