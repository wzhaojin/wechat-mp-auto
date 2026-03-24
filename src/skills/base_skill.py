"""
微信公众号自动化 - 基础 Skill 类
"""

import requests
import json
from typing import Optional, Dict, Any
from token_manager import TokenManager
from config import Config
from exceptions import APIError, get_error_message


class BaseSkill:
    """基础 Skill 类"""
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        self._token_manager = token_manager
        self._config = Config()
    
    @property
    def token_manager(self) -> TokenManager:
        if self._token_manager is None:
            self._token_manager = TokenManager.from_config(self._config)
        return self._token_manager
    
    @property
    def access_token(self) -> str:
        return self.token_manager.get_access_token()
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, retry: bool = True) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"https://api.weixin.qq.com{endpoint}"
        
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        headers = {"Content-Type": "application/json"}
        
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=30)
        else:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
            response = requests.post(url, params=params, data=payload, headers=headers, timeout=30)
        
        result = response.json()
        
        errcode = result.get("errcode", 0)
        if errcode != 0:
            if retry and errcode in [40001, 40014, 42001]:
                self.token_manager.refresh_token()
                params["access_token"] = self.access_token
                return self._request(method, endpoint, data, params, retry=False)
            raise APIError(errcode, result.get("errmsg", get_error_message(errcode)))
        
        return result
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self._request("POST", endpoint, data=data)
