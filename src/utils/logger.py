"""
微信公众号自动化 - 日志工具
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    def __init__(self, name: str = "wechat-mp-auto"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            console = logging.StreamHandler(sys.stdout)
            console.setLevel(logging.INFO)
            log_dir = Path.home() / ".cache" / "wechat-mp-auto" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"wechat-mp-auto_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(console)
            self.logger.addHandler(file_handler)
    
    def _mask(self, msg: str) -> str:
        import re
        msg = re.sub(r'(appid|secret|token)["\s:=]+([a-zA-Z0-9]{4})[a-zA-Z0-9]*', r'\1: \2****', msg, flags=re.IGNORECASE)
        return msg
    
    def info(self, msg: str):
        self.logger.info(self._mask(msg))
    
    def error(self, msg: str):
        self.logger.error(self._mask(msg))


logger = Logger()
