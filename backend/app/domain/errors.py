from __future__ import annotations

from typing import TypeVar


class AppException(Exception):
    """Base application exception."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AuthException(AppException):
    """Authentication/authorization errors (1000-1999)."""
    pass


class ParamException(AppException):
    """Parameter validation errors (2000-2999)."""
    pass


class ServerException(AppException):
    """Server internal errors (5000-5999)."""
    pass


class codes:
    """对外错误码常量。

    数值就是契约，**一律不改**。历史上有几组不同语义共用同一个数值
    （见下方注释），这里只给它们各自的名字，不做归并。
    """

    # ---------- 1000-1999 认证 / 权限 ----------
    UNAUTHORIZED = 1001            # 未登录 / 邮箱或密码错误
    FORBIDDEN = 1002               # 无权限

    # ---------- 2000-2999 参数 ----------
    ENGLISH_THEME_NOT_FOUND = 2008
    ENGLISH_THEME_NOT_READY = 2009

    USERNAME_TAKEN = 2010          # auth：用户名已被使用
    EMAIL_TAKEN = 2011             # auth：邮箱已被注册
    # 下面两个与上面两个撞号（历史遗留，hanzi 与 auth 各用各的）
    HANZI_NOT_FOUND = 2010         # hanzi：级别不存在 / 字条不存在
    HANZI_DUPLICATE = 2011         # hanzi：级别名称已存在 / 该字已存在
    HANZI_LEVEL_NOT_EMPTY = 2012
    HANZI_TOO_FEW_LEARNED = 2013

    T2I_TEMPLATE_CODE_NOT_FOUND = 2020   # template_code 不存在 / 任务所属模板已删除
    T2I_PAGINATION_INVALID = 2021
    T2I_ITEM_INVALID = 2022
    T2I_TASK_NOT_FOUND = 2023
    T2I_TASK_GENERATING = 2024
    T2I_IMAGE_NOT_FOUND = 2025
    T2I_IMAGE_NOT_SUCCEEDED = 2026
    T2I_IMAGE_IN_USE = 2027
    T2I_TEMPLATE_CODE_INVALID = 2030
    T2I_TEMPLATE_NAME_INVALID = 2031
    T2I_TEMPLATE_PROMPT_INVALID = 2032
    T2I_TEMPLATE_CODE_TAKEN = 2033
    T2I_TEMPLATE_NOT_FOUND = 2034
    T2I_TEMPLATE_BUILTIN = 2035
    T2I_TEMPLATE_IN_USE = 2036

    # ---------- 5000-5999 服务端 ----------
    # 注意：AI_GENERATE_FAILED 历史上走的是 ParamException（练习文本生成），
    # 数值虽在 5xxx 段，异常类型不能改。
    AI_GENERATE_FAILED = 5000
    AI_UNAVAILABLE = 5001
    PHOTO_DIR_NOT_FOUND = 5001     # 与 AI_UNAVAILABLE 撞号（历史遗留）
    PHOTO_DIR_UNREADABLE = 5002


T = TypeVar("T")


def ensure_found(value: T | None, code: int, message: str) -> T:
    """查不到就抛 ParamException，查到就原样返回（收编三行守卫样板）。"""
    if value is None:
        raise ParamException(code, message)
    return value
