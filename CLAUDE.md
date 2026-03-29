# RobertGate

## 项目概述
全栈 Web 应用，前后端分离架构。

## 技术栈
- 前端：React 18 + TypeScript + Tailwind CSS
- 后端：Python 3.11 + FastAPI + DDD 架构
- API：RESTful，统一前缀 /api/v1

## 项目结构
```
RobertGate/
├── frontend/          # React 前端
├── backend/           # FastAPI 后端
├── docs/              # 文档（API 定义、UI 设计等）
├── .claude/           # Claude Code 规则与命令
│   ├── rules/         # 代码规范（api、frontend、backend、ui-style）
│   └── commands/      # 自定义命令（feature）
└── CLAUDE.md
```

## 常用命令

### 前端
```bash
cd frontend
npm install          # 安装依赖
npm run dev          # 启动开发服务器 (http://localhost:3000)
npm run build        # 生产构建
npm run preview      # 预览生产构建
npm run lint         # 代码检查
npm run type-check   # TypeScript 类型检查
```

### 后端
```bash
cd backend
uv venv                                # 创建虚拟环境
source .venv/bin/activate              # 激活虚拟环境
uv pip install -r requirements.txt     # 安装依赖
uv run uvicorn app.main:app --reload   # 启动开发服务器 (http://localhost:8000)
uv run pytest                          # 运行所有测试
uv run pytest tests/unit/              # 仅单元测试
uv run pytest tests/integration/       # 仅集成测试
uv run pytest --cov=app                # 测试覆盖率
```

## 开发工作流
1. 使用 `/idea <name>` 需求探索
2. 使用 `/feature <name>` 启动新功能开发
3. 流程：UI 设计 -> API 定义 -> 前端实现 -> 后端实现 -> 联调
4. 每个步骤完成后暂停，等待确认再继续

## 工作流提醒
- 实现新功能前必须调用 brainstorming skill，先探索需求和设计方案
- 前端开发前必须调用 ui-ux-pro-max skill，确保高质量的设计输出
- 实现功能或修复 bug 前优先调用 test-driven-development skill

## 规范速查
- API 规范：`.claude/rules/api.md`
- 前端规范：`.claude/rules/frontend.md`
- 后端规范：`.claude/rules/backend.md`
- UI 风格：`.claude/rules/ui-style.md`
