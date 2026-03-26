---
paths:
  - frontend/**/*.tsx
  - frontend/**/*.ts
  - frontend/**/*.css
---
# 前端代码规范

## 技术栈
- React 18+，函数组件 + Hooks，禁止使用 class 组件
- TypeScript 严格模式
- Tailwind CSS，禁止内联 style，除非动态值无法用 Tailwind 表达
- React Router 处理路由

## 目录结构
frontend/src/
├── components/        # 可复用组件
│   ├── ui/            # 基础 UI 组件（Button、Input 等）
│   └── layout/        # 布局组件（Header、Footer 等）
├── pages/             # 页面级组件，对应路由
├── hooks/             # 自定义 Hooks
├── services/          # API 请求封装
├── store/             # 状态管理
├── types/             # TypeScript 类型定义
└── utils/             # 工具函数

## 代码规范
- 组件文件名使用 PascalCase，如 LoginPage.tsx
- Hooks 文件名使用 camelCase，以 use 开头，如 useAuth.ts
- 每个组件只做一件事，超过 200 行考虑拆分
- API 请求统一放在 services/ 下，页面组件不直接调用 fetch
- 使用 React Query 或 SWR 管理服务端状态

## 构建与运行
```bash
cd frontend
npm install          # 安装依赖
npm run dev          # 开发服务器 http://localhost:3000
npm run build        # 生产构建
npm run lint         # 代码检查
npm run type-check   # TypeScript 类型检查
```

## 禁止
- 禁止在组件内直接写 API URL，统一使用环境变量或常量
- 禁止使用 any 类型
- 禁止直接操作 DOM
