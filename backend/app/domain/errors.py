from __future__ import annotations

from typing import TypeVar


class AppException(Exception):
    """Base application exception.

    `data` 可选：个别业务错误（如 ai-videos 的过期清单）需要在统一错误
    响应的 data 字段里携带结构化内容，默认 None 不影响既有调用方。
    """

    def __init__(self, code: int, message: str, data: object = None) -> None:
        self.code = code
        self.message = message
        self.data = data
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
    PARAM_INVALID = 2000           # 中间件兜底通用码：ValueError 未细分错误码时的兜底

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
    LEGAL_CONTENT_EMPTY = 2001     # legal：content 为空或全空白
    LEGAL_CONTENT_TOO_LONG = 2003  # legal：content 超过 2000 字
    # 与 HANZI_NOT_FOUND / USERNAME_TAKEN 撞号（延续"各业务用各的"惯例）
    LEGAL_ARTICLE_NOT_FOUND = 2010

    # ai-videos（延续"各业务用各的"惯例，数值即 docs/api/ai-videos.md 的契约）
    AV_PARAM_INVALID = 2001            # 与 LEGAL_CONTENT_EMPTY 撞号
    AV_CHARACTER_IN_USE = 2002
    AV_PRECONDITION_FAILED = 2003      # 与 LEGAL_CONTENT_TOO_LONG 撞号
    AV_STALE_CONFIRM_REQUIRED = 2004
    AV_SHOTS_CONFIRM_REQUIRED = 2005
    AV_ASSET_BUSY = 2006
    AV_NOT_FOUND = 2007

    T2I_TEMPLATE_CODE_INVALID = 2030
    T2I_TEMPLATE_NAME_INVALID = 2031
    T2I_TEMPLATE_PROMPT_INVALID = 2032
    T2I_TEMPLATE_CODE_TAKEN = 2033
    T2I_TEMPLATE_NOT_FOUND = 2034
    T2I_TEMPLATE_BUILTIN = 2035
    T2I_TEMPLATE_IN_USE = 2036

    # invest-reports（投资报告 Agent）
    IR_PARAM_INVALID = 2040
    IR_NOT_FOUND = 2041
    IR_TEMPLATE_NOT_READY = 2042
    IR_SOURCE_UNPARSEABLE = 2043
    IR_CHAPTER_BUSY = 2044
    IR_EXPORT_BLOCKED = 2045
    IR_CONFIRM_REQUIRED = 2046

    # ---------- 5000-5999 服务端 ----------
    # 注意：AI_GENERATE_FAILED 历史上走的是 ParamException（练习文本生成），
    # 数值虽在 5xxx 段，异常类型不能改。
    INTERNAL_ERROR = 5000          # 中间件兜底通用码：未捕获异常的兜底
    AI_GENERATE_FAILED = 5000
    AI_UNAVAILABLE = 5001
    PHOTO_DIR_NOT_FOUND = 5001     # 与 AI_UNAVAILABLE 撞号（历史遗留）
    PHOTO_DIR_UNREADABLE = 5002
    LEGAL_AI_FAILED = 5001         # legal：模型服务调用失败（与 AI_UNAVAILABLE 同值）
    LEGAL_KB_NOT_READY = 5002      # legal：知识库索引未就绪（与 PHOTO_DIR_UNREADABLE 撞号）
    AV_UPSTREAM_FAILED = 5001      # ai-videos：SiliconFlow 上游调用失败（撞号惯例）
    AV_UPSTREAM_QUOTA = 5002       # ai-videos：余额不足 / Key 失效（全局暂停队列）
    AV_COMPOSE_FAILED = 5003
    IR_UPSTREAM_FAILED = 5001       # invest-reports：LLM/检索上游失败（撞号惯例）
    IR_UPSTREAM_QUOTA = 5002        # invest-reports：OpenRouter 余额/Key 全局错误
    IR_EXPORT_FAILED = 5004


T = TypeVar("T")


def ensure_found(value: T | None, code: int, message: str) -> T:
    """查不到就抛 ParamException，查到就原样返回（收编三行守卫样板）。"""
    if value is None:
        raise ParamException(code, message)
    return value
