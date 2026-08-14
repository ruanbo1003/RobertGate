---
paths:
  - backend/**/*.py
---
# 后端代码规范

## 技术栈
- Python 3.11+
- FastAPI
- 架构模式：DDD（领域驱动设计）

## 目录结构
backend/
├── app/
│   ├── main.py                  # 应用入口（组合根，工厂函数装配依赖）
│   ├── config.py                 # Settings（环境变量）
│   ├── domain/                  # 领域层
│   │   ├── models/               # 领域模型（SQLAlchemy 2.0 Mapped 实体，兼任 ORM 模型）
│   │   ├── repositories/         # 仓储接口（Protocol）+ UnitOfWork 接口
│   │   └── errors.py             # 异常类型 + 错误码常量（codes）
│   ├── application/              # 应用层
│   │   ├── ports.py               # 出站端口接口（如 AIClient）
│   │   ├── services/              # 应用服务（用例，事务边界）
│   │   └── dto/                   # 出参 DTO（Pydantic）
│   ├── infrastructure/           # 基础设施层
│   │   ├── database/              # 引擎/会话/迁移
│   │   ├── repositories/          # 仓储实现（含 UnitOfWork 实现）
│   │   ├── ai/                    # AI 客户端实现（LLM/Mock/工厂）
│   │   ├── security/              # JWT、密码哈希
│   │   ├── data/                  # 静态数据（如英语主题词库）
│   │   ├── tasks.py                # 后台任务/调度
│   │   └── logging.py              # 日志配置
│   └── interfaces/               # 接口层
│       └── api/
│           ├── routers/            # 路由（只做参数校验 + 调用 service）
│           ├── schemas/            # 请求/响应 Schema（含 PatchModel 等公共基类）
│           ├── deps.py             # FastAPI 依赖注入（当前用户、各 service 组装）
│           ├── response.py         # 统一响应包装（ApiResponse）
│           └── middleware.py       # 异常 -> 统一错误响应的转换
└── tests/
    ├── unit/                    # 单元测试（domain/application 为主，mock 仓储）
    ├── integration/              # 集成测试（预留，当前为空）
    ├── smoke/                   # 真实起服冒烟 + OpenAPI 快照回归
    └── conftest.py

## DDD 规范
- 适度充血：ORM 模型（SQLAlchemy 2.0 Mapped）兼任领域模型，状态机与不变量收进 domain；
  domain 不依赖 FastAPI/基础设施，仅依赖 SQLAlchemy 声明
- 业务逻辑只写在 domain/ 和 application/ 层
- routers 只做参数校验和调用 application service，不写业务逻辑
- 仓储接口（Protocol）定义在 domain/repositories，实现在 infrastructure/repositories
- 事务边界在 application service：通过 UnitOfWork，一个用例一次 commit
- 错误码常量统一在 domain/errors.py 的 codes 里维护，不在各层散落硬编码数字

## 构建与运行
```bash
cd backend
uv venv                                # 创建虚拟环境
source .venv/bin/activate              # 激活虚拟环境
uv pip install -r requirements.txt     # 安装依赖
uv run uvicorn app.main:app --reload   # 开发服务器 http://localhost:8000
uv run pytest                          # 运行所有测试
uv run pytest tests/unit/              # 仅单元测试
uv run pytest tests/integration/       # 仅集成测试
uv run pytest --cov=app                # 测试覆盖率
```
`pytest.ini` 已配置 `testpaths = tests`、`asyncio_mode = auto`：
`pytest`/`uv run pytest` 不带路径参数即可发现 `tests/` 下全部用例，
异步测试函数按 `asyncio` 模式原生调度执行。

## 测试规范
- 新功能必须附带单元测试
- 测试文件命名：test_<被测模块>.py
- 使用 pytest + pytest-asyncio
- domain 层测试不允许依赖数据库，使用 mock
- 测试覆盖率目标 80%+
