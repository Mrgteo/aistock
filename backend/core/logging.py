"""
统一日志系统配置
"""
import logging
import sys
from typing import Optional

# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 全局日志级别
LOG_LEVEL = logging.INFO


def setup_logger(
    name: str,
    level: int = LOG_LEVEL,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    创建配置好的logger

    Args:
        name: logger名称，通常使用__name__
        level: 日志级别
        log_file: 可选的文件路径

    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取logger的快捷方法

    Args:
        name: logger名称，通常使用__name__

    Returns:
        Logger实例
    """
    return setup_logger(name)


# 预配置的模块logger
def get_app_logger(name: str) -> logging.Logger:
    """获取应用模块logger"""
    return setup_logger(f"backend.{name}")


# 禁用过于冗余的第三方库日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
