"""
微信公众号自动化 - 自定义异常
"""

import time
import random
import requests
from functools import wraps
from typing import Optional, Dict, Any, Callable


class WeChatAutoException(Exception):
    """基础异常类"""
    pass


class CredentialError(WeChatAutoException):
    """凭证错误"""
    pass


class TokenError(WeChatAutoException):
    """Token错误"""
    pass


class APIError(WeChatAutoException):
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"错误码 {errcode}: {errmsg}")


class NetworkError(WeChatAutoException):
    """网络请求错误"""
    pass


class ValidationError(WeChatAutoException):
    """参数验证错误"""
    pass


# 完整的微信错误码映射表（从 wechat-allauto-gzh 借鉴）
ERROR_CODES: Dict[int, str] = {
    -1: "系统繁忙，请稍后再试",
    0: "请求成功",
    # Token相关 40001-40029
    40001: "access_token 已过期或无效",
    40002: "不合法的凭证类型",
    40003: "不合法的 OpenID",
    40004: "不合法的媒体文件类型",
    40005: "不合法的文件类型",
    40006: "不合法的文件大小",
    40007: "不合法的媒体文件 id",
    40008: "不合法的消息类型",
    40009: "不合法的图片文件大小",
    40010: "不合法的语音文件大小",
    40011: "不合法的视频文件大小",
    40012: "不合法的缩略图文件大小",
    40013: "不合法的 AppID",
    40014: "不合法的 access_token",
    40015: "不合法的菜单类型",
    40016: "不合法的按钮个数",
    40017: "不合法的按钮类型",
    40018: "不合法的按钮名字长度",
    40019: "不合法的按钮 KEY 长度",
    40020: "不合法的按钮 URL 长度",
    40021: "不合法的菜单版本号",
    40022: "不合法的子菜单级数",
    40023: "不合法的子菜单按钮个数",
    40024: "不合法的子菜单按钮类型",
    40025: "不合法的子菜单按钮名字长度",
    40026: "不合法的子菜单按钮 KEY 长度",
    40027: "不合法的子菜单按钮 URL 长度",
    40028: "不合法的自定义菜单使用用户",
    40029: "不合法的 oauth_code",
    40030: "不合法的 refresh_token",
    40031: "不合法的 openid 列表",
    40032: "不合法的 openid 列表长度",
    40033: "不合法的请求字符",
    40035: "不合法的参数",
    40038: "不合法的请求格式",
    40039: "不合法的 URL 长度",
    40048: "不合法的 url 域名",
    40050: "不合法的 article_tag 标签",
    40051: "不合法的 article_tag 标签长度",
    40060: "不合法的 article_id",
    40061: "不合法的 article_id 数量",
    # 41000-41009
    41001: "缺少 access_token 参数",
    41002: "缺少 appid 参数",
    41003: "缺少 refresh_token 参数",
    41004: "缺少 secret 参数",
    41005: "缺少多媒体文件数据",
    41006: "缺少 media_id 参数",
    41007: "缺少子菜单数据",
    41008: "缺少 oauth code",
    41009: "缺少 openid",
    # 42000-42002
    42001: "access_token 超时",
    42002: "refresh_token 超时",
    # 43000-43005
    43001: "需要 GET 请求",
    43002: "需要 POST 请求",
    43003: "需要 HTTPS 请求",
    43004: "需要接收者关注",
    43005: "需要好友关系",
    # 44000-44005
    44001: "多媒体文件为空",
    44002: "POST 的数据包为空",
    44003: "图文消息内容为空",
    44004: "文本消息内容为空",
    # 45000-45076
    45001: "多媒体文件大小超过限制",
    45002: "消息内容超过限制",
    45003: "标题字段超过限制",
    45004: "描述字段超过限制",
    45005: "链接字段超过限制",
    45006: "图片链接字段超过限制",
    45007: "语音播放时间超过限制",
    45008: "图文消息超过限制",
    45009: "接口调用超过频率限制",
    45010: "创建菜单个数超过限制",
    45015: "回复时间超过限制",
    45016: "系统分组，不允许修改",
    45017: "分组名字过长",
    45018: "分组数量超过上限",
    45047: "客服接口下行条数超过上限",
    45064: "创建菜单包含未关联的小程序",
    45065: "同样错误的请求过于频繁",
    45072: "content 字段超过长度限制",
    45073: "媒体文件大小超过限制",
    45074: "请求地址不是 mp.weixin.qq.com",
    45075: "图片大小超过限制",
    45076: "草稿箱数量超过限制",
    # 46000-46005
    46001: "不存在媒体数据",
    46002: "不存在的菜单版本",
    46003: "不存在的菜单数据",
    46004: "不存在的用户",
    46005: "草稿不存在",
    # 47000-47001
    47001: "解析 JSON/XML 内容错误",
    # 48000-48008
    48001: "api 未授权",
    48002: "api 禁止",
    48003: "接口无权限",
    48004: "api 的传入 json 无效",
    48005: "api 接口需要 post 请求",
    48006: "api 接口需要 get 请求",
    48008: "api 传入参数不正确",
    # 50000-50006
    50001: "用户未授权该 api",
    50002: "用户受限",
    50003: "用户未关注公众号",
    50004: "用户被加入黑名单",
    50005: "用户被限制",
    50006: "用户未绑定微信",
    # 61000-61020
    61000: "请求参数错误",
    61001: "access_token 无效",
    61002: "refresh_token 无效",
    61003: "appid 无效",
    61004: "openid 无效",
    61005: "appsecret 无效",
    61006: "grant_type 无效",
    61007: "code 无效",
    61008: "refresh_token 过期",
    61009: "access_token 过期",
    61010: "access_token 无效",
    61011: "appid 不匹配",
    61012: "refresh_token 无效",
    61013: "openid 无效",
    61014: "appsecret 无效",
    61015: "grant_type 无效",
    61016: "code 无效",
    61017: "refresh_token 过期",
    61018: "access_token 过期",
    61019: "access_token 无效",
    61020: "appid 不匹配",
}


def get_error_message(errcode: int) -> str:
    """获取错误码对应的中文描述"""
    return ERROR_CODES.get(errcode, f"未知错误 ({errcode})")


# Token过期错误码集合（用于自动刷新重试）
TOKEN_EXPIRED_CODES = {40001, 40014, 42001, 40028}


# ==========================================
# 指数退避重试装饰器（从 wechat-allauto-gzh 借鉴）
# ==========================================

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retriable_errors: tuple = (requests.exceptions.RequestException, NetworkError)
):
    """
    指数退避重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        retriable_errors: 可重试的异常类型元组
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retriable_errors as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        # 计算指数退避延迟（添加随机抖动）
                        delay = min(
                            base_delay * (2 ** attempt) + random.uniform(0, 1),
                            max_delay
                        )
                        time.sleep(delay)
                    continue
                
            # 所有重试都失败了
            if isinstance(last_exception, requests.exceptions.Timeout):
                raise NetworkError(f"请求超时，在 {max_retries} 次重试后仍然失败")
            elif isinstance(last_exception, requests.exceptions.ConnectionError):
                raise NetworkError(f"无法连接到服务器，在 {max_retries} 次重试后仍然失败")
            else:
                raise last_exception
        
        return wrapper
    return decorator
