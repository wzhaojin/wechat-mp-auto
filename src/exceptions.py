"""
微信公众号自动化 - 自定义异常
"""


class WeChatAutoException(Exception):
    pass


class CredentialError(WeChatAutoException):
    pass


class TokenError(WeChatAutoException):
    pass


class APIError(WeChatAutoException):
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"错误码 {errcode}: {errmsg}")


ERROR_CODES = {
    -1: "系统繁忙",
    40001: "access_token 无效",
    40013: "appid 错误",
    40125: "appsecret 错误",
    40164: "IP 不在白名单",
    41002: "缺少 appid",
    41004: "缺少 secret",
    42001: "access_token 过期",
    45009: "频率限制",
}


def get_error_message(errcode: int) -> str:
    return ERROR_CODES.get(errcode, f"未知错误 ({errcode})")
