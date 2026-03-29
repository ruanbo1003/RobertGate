# 新功能开发流程

## 使用方式
/feature <feature-name>

参数 `<feature-name>` 对应 PRD 文件路径：`docs/prd/<feature-name>.md`

示例：`/feature auth` -> 读取 `docs/prd/auth.md`

## 流程

### Step 1 - 阅读 PRD
- 读取 `docs/prd/$ARGUMENTS.md`，理解完整需求
- 如果文件不存在，提示用户先创建 PRD

### Step 2 - UI 设计
- 根据 `docs/prd/$ARGUMENTS.md` 分析涉及的页面和交互
- **严格遵循 `.claude/rules/ui-style.md` 中的设计规范**
- 用 Pencil MCP 设计 UI 效果图
- 列出所有 UI 组件清单，等待确认

**暂停，等待用户确认 UI 设计后继续**

### Step 3 - API 定义
- 根据 UI 和 PRD，定义所需的 API 接口
- 输出接口文档，包含：
  - 路由、方法、请求参数、响应格式
  - 错误码
- 保存到 `docs/api/$ARGUMENTS.md`

**暂停，等待用户确认 API 定义后继续**

### Step 4 - 前端实现
- 读取 `docs/prd/$ARGUMENTS.md` 和 `docs/api/$ARGUMENTS.md`
- **严格遵循 `.claude/rules/ui-style.md` 和 `.claude/rules/frontend.md`**
- API 请求用 mock 数据，不依赖后端

**暂停，等待用户确认前端实现后继续**

### Step 5 - 后端实现
- 根据 API 文档实现后端接口
- 遵循 `.claude/rules/backend.md` 规范
- 包含单元测试

### Step 6 - 联调
- 将前端 mock 替换为真实 API 调用
- 验证前后端数据格式一致
