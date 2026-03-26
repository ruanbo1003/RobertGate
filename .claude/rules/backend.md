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
│   ├── main.py                  # 应用入口
│   ├── domain/                  # 领域层
│   │   ├── models/              # 领域模型（实体、值对象）
│   │   └── repositories/        # 仓储接口（抽象）
│   ├── application/             # 应用层
│   │   ├── services/            # 应用服务（用例）
│   │   └── dto/                 # 数据传输对象
│   ├── infrastructure/          # 基础设施层
│   │   ├── repositories/        # 仓储实现
│   │   └── database/            # 数据库配置
│   └── interfaces/              # 接口层
│       └── api/
│           ├── routers/         # 路由
│           └── schemas/         # 请求/响应 Schema
└── tests/
    ├── unit/                    # 单元测试
    ├── integration/             # 集成测试
    └── conftest.py

## DDD 规范
- 领域模型不依赖框架，纯 Python 类
- 业务逻辑只写在 domain/ 和 application/ 层
- routers 只做参数校验和调用 application service，不写业务逻辑
- 仓储接口定义在 domain/，实现在 infrastructure/

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

## 测试规范
- 新功能必须附带单元测试
- 测试文件命名：test_<被测模块>.py
- 使用 pytest + pytest-asyncio
- domain 层测试不允许依赖数据库，使用 mock
- 测试覆盖率目标 80%+
